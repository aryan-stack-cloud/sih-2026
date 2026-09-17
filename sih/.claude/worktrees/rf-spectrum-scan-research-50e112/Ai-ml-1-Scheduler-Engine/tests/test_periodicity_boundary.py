"""The Ai-ml-2 boundary, and the training-only stand-in for it.

Two things are being protected here:

1. On the inference path, ``periodicity_phase`` and ``periodicity_confidence`` must be whatever
   the Backend sent -- never recomputed locally. Ai-ml-1 does not call Ai-ml-2 (API_CONTRACT.md
   Section 0), and if this service quietly overwrote those features, the Backend and the agent
   would be reasoning about different states.

2. The training-only estimator must not claim confident periodicity where there is none. Ai-ml-2
   Level 7 requires low confidence for the four non-periodic behavior classes, because the
   Backend feeds these features for *every* band, not just periodic ones.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.contract import StateVector
from ml.environments.environment import make_env, null_periodicity_env
from ml.environments.state import StateBuilder
from ml.features.periodicity_provider import (
    LocalPeriodicityProvider,
    NullPeriodicityProvider,
    PeriodicityProvider,
)
from ml.inference.inference import InferenceEngine
from ml.model_registry import ModelRegistry
from ml.utils.config import load_scenario


# -- protocol conformance ----------------------------------------------------------------------

@pytest.mark.parametrize("provider", [NullPeriodicityProvider(), LocalPeriodicityProvider()])
def test_providers_satisfy_the_protocol(provider):
    assert isinstance(provider, PeriodicityProvider)


def test_null_provider_reports_nothing():
    p = NullPeriodicityProvider()
    p.reset(8)
    phase, confidence = p.features(100)
    assert np.all(phase == 0.0) and np.all(confidence == 0.0)


# -- the training-only estimator ------------------------------------------------------------------

def test_estimator_stays_silent_below_the_minimum_sample_count():
    p = LocalPeriodicityProvider(min_samples=4)
    p.reset(4)
    for t in (0, 10):
        p.observe_detection(0, t)
    _, confidence = p.features(20)
    assert confidence[0] == 0.0


def test_estimator_recovers_a_clean_constant_period():
    p = LocalPeriodicityProvider(buffer_size=16, min_samples=4)
    p.reset(4)
    for t in range(0, 200, 20):     # period exactly 20
        p.observe_detection(1, t)
    phase, confidence = p.features(190)
    assert confidence[1] > 0.8
    # 190 is 10 steps past the last detection at 180 -> half a period elapsed.
    assert phase[1] == pytest.approx(0.5, abs=0.05)


def test_confidence_rises_as_consistent_samples_accumulate():
    p = LocalPeriodicityProvider(buffer_size=16, min_samples=4)
    p.reset(2)
    seen = []
    for i, t in enumerate(range(0, 320, 20)):
        p.observe_detection(0, t)
        if i >= 4:
            seen.append(p.features(t)[1][0])
    assert seen == sorted(seen)
    assert seen[-1] > seen[0]


def test_confidence_degrades_with_jitter():
    clean = LocalPeriodicityProvider(min_samples=4)
    clean.reset(1)
    for t in range(0, 200, 20):
        clean.observe_detection(0, t)

    jittered = LocalPeriodicityProvider(min_samples=4)
    jittered.reset(1)
    rng = np.random.default_rng(0)
    t = 0
    for _ in range(10):
        t += 20 + int(rng.integers(-12, 13))
        jittered.observe_detection(0, max(0, t))

    assert jittered.features(200)[1][0] < clean.features(200)[1][0]


def test_no_false_confidence_on_a_random_emitter():
    """Ai-ml-2 Level 7: a confident-but-wrong periodicity claim is worse than no claim."""
    p = LocalPeriodicityProvider(min_samples=4)
    p.reset(1)
    rng = np.random.default_rng(1)
    t = 0
    for _ in range(16):
        t += int(rng.integers(1, 40))
        p.observe_detection(0, t)
    assert p.features(t + 5)[1][0] < 0.6


def test_buffer_is_bounded():
    p = LocalPeriodicityProvider(buffer_size=8)
    p.reset(1)
    for t in range(100):
        p.observe_detection(0, t)
    assert len(p.state(0)["timestamps"]) == 8


def test_duplicate_timestamps_are_ignored():
    p = LocalPeriodicityProvider()
    p.reset(1)
    for _ in range(5):
        p.observe_detection(0, 42)
    assert p.state(0)["timestamps"] == [42]


# -- the environment wiring ------------------------------------------------------------------------

def test_periodicity_features_carry_signal_during_training():
    cfg = load_scenario("B")
    cfg["duration_steps"] = 600
    env = make_env(cfg, seed=42)
    env.reset()
    for t in range(600):
        env.step(t % cfg["bands"])
    _, confidence = env.periodicity.features(env.t)
    assert confidence.max() > 0.0, "training runs must not leave the features dead at zero"


def test_null_provider_env_pins_both_features_to_zero():
    cfg = load_scenario("B")
    cfg["duration_steps"] = 300
    env = null_periodicity_env(cfg, seed=42)
    env.reset()
    for t in range(300):
        env.step(t % cfg["bands"])
    state = env.state_vector()
    assert all(b["periodicity_phase"] == 0.0 for b in state["bands"])
    assert all(b["periodicity_confidence"] == 0.0 for b in state["bands"])


# -- the inference path ------------------------------------------------------------------------------

def test_inference_uses_the_backend_supplied_periodicity_verbatim(tmp_path):
    """The features must survive the StateVector -> agent-vector conversion untouched."""
    engine = InferenceEngine(ModelRegistry(tmp_path))
    state = _state_with_periodicity(num_bands=6, band=2, phase=0.75, confidence=0.9)

    vector = StateBuilder.from_contract(state.model_dump()).to_vector()
    bands = vector[: 7 * 6].reshape(6, 7)
    assert bands[2, 3] == pytest.approx(0.75)   # periodicity_phase
    assert bands[2, 4] == pytest.approx(0.9)    # periodicity_confidence

    action, _, _ = engine.decide("sim_abcd1234", state, "bandit")
    assert 0 <= action.next_band < 6


def _state_with_periodicity(num_bands: int, band: int, phase: float, confidence: float):
    return StateVector.model_validate(
        {
            "bands": [
                {
                    "band_id": b,
                    "time_since_last_scan": 3,
                    "recent_detection_rate_ewma": 0.1,
                    "consecutive_misses": 1,
                    "periodicity_phase": phase if b == band else 0.0,
                    "periodicity_confidence": confidence if b == band else 0.0,
                    "band_priority_weight": 1.0,
                    "tuning_cost_to_band": 1,
                }
                for b in range(num_bands)
            ],
            "receiver": {
                "tuned_bands": [0],
                "dwell_remaining_ms": 0,
                "tuning_delay_countdown_ms": 0,
            },
        }
    )
