"""EWEnvironment: Gymnasium conformance, contract shape, receiver physics (Ai-ml-1 Level 2 DoD).

The Level 2 Definition of Done is that step/reset round-trip cleanly *against the shared
StateVector schema* -- not against a shape this service invented. So these tests validate the
environment's output with the same pydantic models the API uses.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.contract import StateVector
from ml.environments.environment import EWEnvironment, make_env
from ml.environments.receiver import ReceiverConfig
from ml.environments.state import StateBuilder, vector_from_contract
from ml.utils.config import SCENARIO_IDS, load_scenario


@pytest.fixture
def env() -> EWEnvironment:
    return make_env(load_scenario("A"), seed=42)


def test_observation_shape_matches_the_declared_space(env):
    obs, info = env.reset()
    assert obs.shape == (StateBuilder.vector_size(env.num_bands),)
    assert obs.dtype == np.float32
    assert env.observation_space.contains(obs)
    assert info["scenario_id"] == "A"


def test_action_space_is_discrete_over_bands(env):
    assert env.action_space.n == env.num_bands


def test_random_policy_runs_a_full_episode_without_crashing(env):
    env.reset()
    rng = np.random.default_rng(0)
    steps = 0
    while True:
        _, _, terminated, truncated, _ = env.step(int(rng.integers(0, env.num_bands)))
        steps += 1
        if terminated or truncated:
            break
    assert steps == env.duration_steps
    assert not terminated and truncated  # episodes end by truncation at t = T (Section 10.4)


def test_long_scenario_runs_three_thousand_steps():
    e = make_env(load_scenario("D"), seed=7)
    e.reset()
    for t in range(e.duration_steps):
        e.step(t % e.num_bands)
    assert e.t == 3000


def test_state_vector_validates_against_the_shared_contract(env):
    env.reset()
    for t in range(30):
        env.step(t % env.num_bands)
    # Raises if any field name, type or bound drifts from API_CONTRACT.md Section 4.
    parsed = StateVector.model_validate(env.state_vector())
    assert len(parsed.bands) == env.num_bands
    assert [b.band_id for b in parsed.bands] == list(range(env.num_bands))


def test_contract_round_trip_reproduces_the_agent_observation(env):
    obs, _ = env.reset()
    for t in range(25):
        obs, *_ = env.step((t * 5) % env.num_bands)
    assert np.allclose(vector_from_contract(env.state_vector()), obs, atol=1e-6)


def test_from_contract_is_order_independent(env):
    env.reset()
    env.step(3)
    sv = env.state_vector()
    shuffled = {"bands": list(reversed(sv["bands"])), "receiver": sv["receiver"]}
    assert np.allclose(vector_from_contract(shuffled), vector_from_contract(sv))


def test_from_contract_rejects_a_non_contiguous_band_range():
    sv = {
        "bands": [
            {"band_id": 0, "time_since_last_scan": 0, "recent_detection_rate_ewma": 0.0,
             "consecutive_misses": 0, "periodicity_phase": 0.0, "periodicity_confidence": 0.0,
             "band_priority_weight": 1.0, "tuning_cost_to_band": 0},
            {"band_id": 5, "time_since_last_scan": 0, "recent_detection_rate_ewma": 0.0,
             "consecutive_misses": 0, "periodicity_phase": 0.0, "periodicity_confidence": 0.0,
             "band_priority_weight": 1.0, "tuning_cost_to_band": 1},
        ],
        "receiver": {"tuned_bands": [0], "dwell_remaining_ms": 0, "tuning_delay_countdown_ms": 0},
    }
    with pytest.raises(ValueError, match="contiguous"):
        vector_from_contract(sv)


def test_receiver_observes_k_contiguous_bands(env):
    env.reset()
    env.step(5)
    assert env.history[-1]["scanned_bands"] == [5, 6]


def test_receiver_block_wraps_at_the_top_of_the_spectrum(env):
    env.reset()
    env.step(env.num_bands - 1)
    assert env.history[-1]["scanned_bands"] == [env.num_bands - 1, 0]


def test_step_without_reset_is_an_error():
    e = EWEnvironment(num_bands=8, duration_steps=10)
    with pytest.raises(RuntimeError, match="call reset"):
        e.step(0)


def test_tuning_delay_shorter_than_dwell_blocks_the_observation():
    """PRD Section 9.1: the tuning delay must fully elapse before a valid observation."""
    cfg = ReceiverConfig(step_ms=10, dwell_ms=8, tuning_delay_ms=5, bandwidth_k=1)
    assert not cfg.retune_is_observable
    e = EWEnvironment(num_bands=8, duration_steps=20, receiver_config=cfg, seed=1)
    e.reset()
    e.step(4)  # retunes away from band 0
    assert e.history[-1]["valid"] is False
    assert e.history[-1]["scanned_bands"] == []
    e.step(4)  # staying put costs no tuning delay
    assert e.history[-1]["valid"] is True


def test_dwell_longer_than_step_is_rejected():
    with pytest.raises(ValueError, match="dwell_ms cannot exceed step_ms"):
        ReceiverConfig(step_ms=5, dwell_ms=10)


def test_staying_on_a_band_is_not_counted_as_a_retune(env):
    env.reset()
    env.step(3)
    env.step(3)
    assert env.history[-1]["retuned"] is False


def test_ground_truth_never_leaks_into_the_observation(env):
    """PRD Section 8.1: ground truth is for scoring only, never given to the scheduler."""
    obs, _ = env.reset()
    active = env.ground_truth.occupancy[0]
    # The only band-activity information in the observation comes from the agent's own scans,
    # which have not happened yet at t=0, so the detection-rate features must all be zero.
    ewma = obs[: 7 * env.num_bands].reshape(env.num_bands, 7)[:, 1]
    assert np.all(ewma == 0.0)
    assert active.any()  # the spectrum is genuinely occupied; the agent just cannot see it


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS)
def test_every_scenario_builds_and_steps(scenario_id):
    cfg = load_scenario(scenario_id)
    e = make_env(cfg, seed=11)
    obs, _ = e.reset()
    assert obs.shape == (StateBuilder.vector_size(cfg["bands"]),)
    for t in range(50):
        obs, reward, _, _, _ = e.step(t % cfg["bands"])
        assert np.isfinite(reward)
    StateVector.model_validate(e.state_vector())
