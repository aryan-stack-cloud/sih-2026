"""Scenario G switching and the pre-switch occupancy baselines for A-F."""

import hashlib

import numpy as np
import pytest

from ml.environments.emitters import BEHAVIOR_CLASSES, build_emitters, summarize
from ml.environments.spectrum import Spectrum
from ml.utils.config import load_scenario
from ml.utils.seeding import make_seed_bundle


BASELINE_SHA256 = {
    "A": "ed193e573cda790aa2ab59dafcfcc8113e9924b1272d087b550771a9181342fd",
    "B": "763a0ce96e627f22ac55346f44e5009af2bdf645f871c2ded1afa0a65553709b",
    "C": "8e671c77a731bc37a244fc309604b32a03415564e8d39a83c25925943a64c06e",
    "D": "5a8b8af9b1a07f4c7811115c062ad0219370d3c8e8e8dd8ea10c395a7c5b326b",
    "E": "285542ad3d28b835be58b8e1e63d5e3050937534b6d18bcbb8c276790ab56459",
    "F": "16f13214b62bc786752acca4b21a0a273da4f543337cfd159d30e4d704f253f8",
}


def generated(sid: str, seed: int):
    cfg = load_scenario(sid)
    rng = make_seed_bundle(seed).ground_truth
    emitters = build_emitters(
        cfg["emitters"], cfg["bands"], cfg["emitter_mix"], rng,
        cfg["high_priority_fraction"], cfg.get("emitter_params"),
    )
    gt = Spectrum(cfg["bands"]).generate_ground_truth(emitters, cfg["duration_steps"], rng)
    return emitters, gt


@pytest.mark.parametrize("sid", "ABCDEF")
def test_pre_switch_ground_truth_is_unchanged(sid):
    emitters, gt = generated(sid, 99)
    assert all(not emitter.regimes for emitter in emitters)
    assert hashlib.sha256(gt.occupancy.tobytes()).hexdigest() == BASELINE_SHA256[sid]


def test_g_switches_class_and_preserves_home_identity_and_statistics():
    emitters, gt = generated("G", 99)
    assert summarize(emitters) == {name: 3 for name in BEHAVIOR_CLASSES}
    assert all(len(e.regimes) >= 2 for e in emitters)
    assert gt.occupancy.shape == (3000, 24)

    for emitter in emitters:
        regimes = emitter.regimes
        assert regimes[0].start == 0
        assert regimes[0].behavior_class == emitter.behavior_class
        assert regimes[0].params == emitter.params
        assert regimes[0].bands == emitter.bands
        assert regimes[-1].end == 3000
        for before, after in zip(regimes, regimes[1:]):
            assert before.end == after.start
            assert before.behavior_class != after.behavior_class
        for regime in regimes:
            assert regime.bands[0] == emitter.bands[0]
            if regime.behavior_class != "agile":
                assert regime.bands == (emitter.bands[0],)
            if regime.behavior_class == "agile":
                assert regime.params["hop_rate"] == 3
            if regime.behavior_class == "intermittent":
                assert regime.params["p_on_to_off"] == 0.4
                assert regime.params["p_off_to_on"] == 0.12
            if regime.behavior_class == "periodic":
                assert regime.params["jitter"] == 4

    # Check each class's activity rate on complete (>=200-step) regimes. The rate
    # windows are wider than sampling variation but distinguish the five generators.
    class_rates = {name: [] for name in BEHAVIOR_CLASSES}
    rng = make_seed_bundle(99).ground_truth
    cfg = load_scenario("G")
    again = build_emitters(15, 24, cfg["emitter_mix"], rng, 0.25, cfg["emitter_params"])
    for emitter in again:
        track = emitter.activity_track(3000, rng)
        for regime in emitter.regimes:
            if regime.end - regime.start >= 200:
                class_rates[regime.behavior_class].append(
                    np.mean(track[regime.start:regime.end] >= 0)
                )
    means = {name: float(np.mean(rates)) for name, rates in class_rates.items()}
    assert means["fixed"] == pytest.approx(0.95, abs=0.05)
    assert means["agile"] == pytest.approx(0.90, abs=0.05)
    assert 0.12 < means["periodic"] < 0.27
    assert 0.10 < means["random"] < 0.22
    assert 0.14 < means["intermittent"] < 0.38
