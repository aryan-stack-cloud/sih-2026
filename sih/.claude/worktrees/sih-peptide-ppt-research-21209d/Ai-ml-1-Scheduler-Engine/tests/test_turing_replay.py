"""Turing replay pipeline.

The pure transforms (frequency binning, TOA quantisation, environment wiring) are tested with
synthetic PDWs and always run. The download is gated behind an HF token and is marked ``turing``
so the default suite stays offline and deterministic:

    pytest -m turing        # requires HF_TOKEN and accepted dataset terms
"""

from __future__ import annotations

import os

import h5py
import numpy as np
import pytest

from ml.agents.baseline_scanner import BaselineScanner
from ml.data.turing_replay import (
    TuringDatasetUnavailable,
    build_occupancy,
    build_replay_ground_truth,
    extract_pdw_features,
    map_frequencies_to_bands,
)
from ml.environments.environment import EWEnvironment
from ml.evaluation.runner import run_episode


# -- frequency binning ---------------------------------------------------------------------------

def test_frequencies_bin_across_the_full_band_range():
    freqs = np.linspace(1.0e9, 2.0e9, 100)
    bands = map_frequencies_to_bands(freqs, num_bands=10)
    assert bands.min() == 0 and bands.max() == 9
    assert set(np.unique(bands)) == set(range(10))


def test_binning_is_monotonic_in_frequency():
    bands = map_frequencies_to_bands([1e9, 1.5e9, 2e9], num_bands=4)
    assert list(bands) == sorted(bands)


def test_binning_preserves_an_uneven_spectrum():
    """Equal-width, not equal-count: crowding in one part of the spectrum must survive."""
    freqs = np.concatenate([np.full(90, 1.05e9), np.linspace(1.5e9, 2.0e9, 10)])
    counts = np.bincount(map_frequencies_to_bands(freqs, 10), minlength=10)
    assert counts[0] == 90


def test_binning_handles_a_single_frequency():
    assert list(map_frequencies_to_bands([1.0e9] * 5, 8)) == [0, 0, 0, 0, 0]


def test_binning_handles_no_pulses():
    assert map_frequencies_to_bands([], 10).size == 0


def test_binning_rejects_zero_bands():
    with pytest.raises(ValueError, match="num_bands must be >= 1"):
        map_frequencies_to_bands([1.0, 2.0], 0)


# -- occupancy construction ------------------------------------------------------------------------

def test_occupancy_spans_the_requested_duration():
    toa = np.linspace(0.0, 1.0, 50)
    bands = np.zeros(50, dtype=np.int32)
    occ = build_occupancy(toa, bands, num_bands=4, duration_steps=100, pulse_dwell_steps=1)
    assert occ.shape == (100, 4)
    assert occ[0, 0] and occ[-1, 0]
    assert not occ[:, 1].any()


def test_pulse_dwell_widens_each_pulse_into_a_catchable_window():
    toa = np.array([0.0])
    bands = np.array([2], dtype=np.int32)
    occ = build_occupancy(toa, bands, num_bands=4, duration_steps=10, pulse_dwell_steps=3)
    assert occ[:, 2].tolist() == [True, True, True, False, False, False, False, False, False, False]


def test_occupancy_of_an_empty_pulse_train_is_empty():
    occ = build_occupancy(np.zeros(0), np.zeros(0, dtype=np.int32), 4, 50)
    assert occ.shape == (50, 4) and not occ.any()


# -- HDF5 reading ------------------------------------------------------------------------------------

def write_h5(path, toa, freq, group=None, names=("toa", "frequency")):
    with h5py.File(path, "w") as f:
        target = f.create_group(group) if group else f
        target.create_dataset(names[0], data=np.asarray(toa))
        target.create_dataset(names[1], data=np.asarray(freq))
    return path


def test_reads_flat_datasets(tmp_path):
    p = write_h5(tmp_path / "flat.h5", [0.0, 1.0, 2.0], [1e9, 1.5e9, 2e9])
    pdw = extract_pdw_features(p)
    assert pdw["toa"].tolist() == [0.0, 1.0, 2.0]
    assert pdw["frequency"].tolist() == [1e9, 1.5e9, 2e9]


def test_reads_nested_groups(tmp_path):
    p = write_h5(tmp_path / "nested.h5", [0.0, 1.0], [1e9, 2e9], group="pulses")
    assert extract_pdw_features(p)["toa"].size == 2


def test_matches_field_name_aliases(tmp_path):
    """The dataset schema is external; alias matching is what keeps this from being brittle."""
    p = write_h5(tmp_path / "aliased.h5", [0.0, 1.0], [1e9, 2e9],
                 names=("Time_of_Arrival", "Centre_Frequency"))
    pdw = extract_pdw_features(p)
    assert pdw["toa"].size == 2 and pdw["frequency"].size == 2


def test_reads_a_compound_pulse_table(tmp_path):
    p = tmp_path / "compound.h5"
    rows = np.array([(0.0, 1e9), (1.0, 2e9)],
                    dtype=[("TOA", "f8"), ("CentreFrequency", "f8")])
    with h5py.File(p, "w") as f:
        f.create_dataset("pdws", data=rows)
    pdw = extract_pdw_features(p)
    assert pdw["toa"].tolist() == [0.0, 1.0]


def test_unrecognised_schema_reports_what_it_actually_found(tmp_path):
    p = tmp_path / "mystery.h5"
    with h5py.File(p, "w") as f:
        f.create_dataset("alpha", data=np.arange(3))
        f.create_dataset("beta", data=np.arange(3))
    with pytest.raises(TuringDatasetUnavailable, match="Fields present"):
        extract_pdw_features(p)


# -- the join back to Module 1 ---------------------------------------------------------------------

def test_replay_ground_truth_drives_the_unmodified_environment(tmp_path):
    """The whole point: swap the ground-truth source, change nothing else."""
    rng = np.random.default_rng(0)
    toa = np.sort(rng.uniform(0, 1000, 4000))
    freq = rng.uniform(1.0e9, 2.0e9, 4000)
    path = write_h5(tmp_path / "replay.h5", toa, freq)

    gt = build_replay_ground_truth([path], num_bands=16, duration_steps=500, pulse_dwell_steps=2)
    assert gt.occupancy.shape == (500, 16)
    assert gt.occupancy.any()

    env = EWEnvironment(num_bands=16, duration_steps=500, ground_truth=gt, seed=42,
                        scenario_id="turing-replay")
    obs, info = env.reset()
    assert info["scenario_id"] == "turing-replay"

    metrics = run_episode(env, BaselineScanner(16, stride=2), seed=42)
    assert metrics.steps == 500
    assert metrics.total_scans > 0
    assert 0.0 <= metrics.pd <= 1.0


def test_replay_state_still_satisfies_the_shared_contract(tmp_path):
    from ml.contract import StateVector

    rng = np.random.default_rng(1)
    path = write_h5(tmp_path / "c.h5", np.sort(rng.uniform(0, 100, 500)),
                    rng.uniform(1e9, 2e9, 500))
    gt = build_replay_ground_truth([path], num_bands=8, duration_steps=100)
    env = EWEnvironment(num_bands=8, duration_steps=100, ground_truth=gt, seed=1)
    env.reset()
    for t in range(50):
        env.step(t % 8)
    StateVector.model_validate(env.state_vector())


# -- the gated download ------------------------------------------------------------------------------

@pytest.mark.turing
@pytest.mark.skipif(not os.environ.get("HF_TOKEN"), reason="requires HF_TOKEN for the gated repo")
def test_downloads_and_replays_a_real_pulse_train():
    from ml.data.turing_replay import load_replay_scenario

    env = load_replay_scenario(num_bands=16, duration_steps=500, num_files=1)
    env.reset()
    metrics = run_episode(env, BaselineScanner(16, stride=2), seed=42)
    assert metrics.steps == 500
    assert env.ground_truth.occupancy.any()
