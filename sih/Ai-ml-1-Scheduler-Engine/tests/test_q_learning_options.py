"""Opt-in refinements of the tabular Q-learner: finer bins, next-band context and agent-side shaping.

Every option defaults to the original behaviour, so these tests pin two things: the new keys equal a plain scalar definition,
and an agent with every option at its default is byte-for-byte the original.
"""

import json

import numpy as np
import pytest

from ml.agents.factory import build_agent
from ml.agents.q_learning_agent import DEFAULT_BINS, FALLBACK_UNIFORM_BINS, QLearningAgent
from ml.environments.environment import EWEnvironment
from ml.environments.state import BAND_FEATURES, NUM_BAND_FEATURES
from ml.evaluation.runner import run_episode

EWMA = "recent_detection_rate_ewma"
AGE = "time_since_last_scan"
MISSES = "consecutive_misses"
E6 = [0.05, 0.15, 0.3, 0.5, 0.75]


# -- plain scalar references (no vectorisation, no cache) ------------------------------------------


def _uniform(value, nbins):
    return int(min(nbins - 1, max(0, int(value * nbins))))


def _edge_bin(value, edges):
    return sum(1 for e in edges if value >= e)   # number of thresholds at or below the value == searchsorted(side="right")


def _reference_keys(obs, n, bins, bin_edges=None, neighbor=(), neighbor_edges=None):
    bin_edges = bin_edges or {}
    neighbor_edges = neighbor_edges or {}
    index = {name: i for i, name in enumerate(BAND_FEATURES)}
    bands = np.asarray(obs[: NUM_BAND_FEATURES * n], dtype=np.float64).reshape(n, NUM_BAND_FEATURES)

    def bin_of(name, value, edges):
        if edges is not None:
            return _edge_bin(value, edges)
        return _uniform(value, bins.get(name, FALLBACK_UNIFORM_BINS))

    keys = []
    for b in range(n):
        key = [bin_of(name, bands[b, index[name]], bin_edges.get(name)) for name in sorted(set(bins) | set(bin_edges))]
        for name in neighbor:
            edges = neighbor_edges.get(name, bin_edges.get(name))
            key.append(bin_of(name, bands[(b + 1) % n, index[name]], edges))
        keys.append(tuple(key))
    return keys


def _original_keys(obs, n, bins):
    """The three-line loop the agent used before these options existed."""
    index = {name: i for i, name in enumerate(BAND_FEATURES)}
    bands = np.asarray(obs[: NUM_BAND_FEATURES * n], dtype=np.float64).reshape(n, NUM_BAND_FEATURES)
    return [
        tuple(int(min(bins[k] - 1, max(0, int(bands[b, index[k]] * bins[k])))) for k in sorted(bins)) for b in range(n)
    ]


def _random_obs(n, seed):
    return np.random.default_rng(seed).random(8 * n + 2)


def _rollout(n=8, steps=60, seed=3):
    """(observation, action, reward, next_observation, info) transitions from a real environment."""
    env = EWEnvironment(num_bands=n, duration_steps=steps, num_emitters=3, seed=seed)
    obs, _ = env.reset(seed=seed)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(steps):
        action = int(rng.integers(0, n))
        nxt, reward, terminated, truncated, info = env.step(action)
        out.append((obs, action, reward, nxt, info))
        obs = nxt
        if terminated or truncated:
            break
    return out


# -- keys equal the scalar definition ----------------------------------------------------------------


@pytest.mark.parametrize("n", [8, 16])
def test_default_keys_equal_the_original_implementation(n):
    agent = QLearningAgent(n)
    for seed in range(5):
        obs = _random_obs(n, seed)
        assert agent._keys(obs) == _original_keys(obs, n, DEFAULT_BINS)


@pytest.mark.parametrize("n", [8, 16])
def test_bin_edges_on_a_listed_feature_replace_its_uniform_bins(n):
    agent = QLearningAgent(n, bin_edges={EWMA: E6})
    for seed in range(5):
        obs = _random_obs(n, seed)
        assert agent._keys(obs) == _reference_keys(obs, n, DEFAULT_BINS, bin_edges={EWMA: E6})


def test_bin_edges_can_add_a_feature_that_has_no_uniform_bins():
    n = 8
    agent = QLearningAgent(n, bin_edges={MISSES: [0.05, 0.15, 0.35, 0.7]})
    obs = _random_obs(n, 11)
    keys = agent._keys(obs)
    assert keys == _reference_keys(obs, n, DEFAULT_BINS, bin_edges={MISSES: [0.05, 0.15, 0.35, 0.7]})
    assert len(keys[0]) == len(DEFAULT_BINS) + 1


@pytest.mark.parametrize("n", [8, 16])
def test_neighbour_features_join_the_key_and_wrap_at_the_top(n):
    agent = QLearningAgent(n, neighbor_features=[EWMA, AGE])
    obs = _random_obs(n, 4)
    keys = agent._keys(obs)
    assert keys == _reference_keys(obs, n, DEFAULT_BINS, neighbor=[EWMA, AGE])
    # band N-1's neighbour is band 0: its trailing bins are band 0's own ewma / age bins
    own0 = dict(zip(sorted(DEFAULT_BINS), keys[0]))
    assert keys[n - 1][-2:] == (own0[EWMA], own0[AGE])


def test_neighbour_bin_edges_override_and_otherwise_follow_the_own_spec():
    n = 8
    obs = _random_obs(n, 5)
    own_spec = QLearningAgent(n, bin_edges={EWMA: E6}, neighbor_features=[EWMA, AGE])
    assert own_spec._keys(obs) == _reference_keys(obs, n, DEFAULT_BINS, bin_edges={EWMA: E6}, neighbor=[EWMA, AGE])
    coarse = QLearningAgent(n, bin_edges={EWMA: E6}, neighbor_features=[EWMA], neighbor_bin_edges={EWMA: [0.15, 0.4]})
    assert coarse._keys(obs) == _reference_keys(
        obs, n, DEFAULT_BINS, bin_edges={EWMA: E6}, neighbor=[EWMA], neighbor_edges={EWMA: [0.15, 0.4]}
    )


@pytest.mark.parametrize("n", [8, 16])
def test_everything_together_matches_the_reference(n):
    kwargs = dict(
        bin_edges={EWMA: E6, MISSES: [0.1, 0.4]},
        neighbor_features=[EWMA, "periodicity_phase"],
        neighbor_bin_edges={EWMA: [0.15, 0.4]},
    )
    agent = QLearningAgent(n, **kwargs)
    for seed in range(4):
        obs = _random_obs(n, 20 + seed)
        assert agent._keys(obs) == _reference_keys(
            obs, n, DEFAULT_BINS, kwargs["bin_edges"], kwargs["neighbor_features"], kwargs["neighbor_bin_edges"]
        )


def test_a_value_on_a_threshold_goes_to_the_upper_bin_and_the_extremes_are_handled():
    n = 8
    agent = QLearningAgent(n, bin_edges={EWMA: [0.25, 0.5]})
    obs = np.zeros(8 * n + 2)
    column = NUM_BAND_FEATURES * 0 + BAND_FEATURES.index(EWMA)
    for band, value in enumerate([0.0, 0.2499, 0.25, 0.4999, 0.5, 1.0, 0.0, 0.0]):
        obs[band * NUM_BAND_FEATURES + column] = value
    ewma_position = sorted(set(DEFAULT_BINS)).index(EWMA)
    assert [k[ewma_position] for k in agent._keys(obs)] == [0, 0, 1, 1, 2, 2, 0, 0]


# -- defaults are the original agent -----------------------------------------------------------------


def test_options_written_out_at_their_defaults_change_nothing():
    plain = QLearningAgent(8)
    explicit = QLearningAgent(
        8, bin_edges=None, neighbor_features=(), neighbor_bin_edges=None, eff_beta=0.0, cov_beta=0.0, align_window=False
    )
    for obs, action, reward, nxt, info in _rollout()[:40]:
        for agent in (plain, explicit):
            agent.observe(info)
            agent.learn(obs, action, reward, nxt)
    assert plain.q_table == explicit.q_table
    assert plain.visit_counts == explicit.visit_counts
    assert plain.hyperparams() == explicit.hyperparams()
    assert set(plain.hyperparams()) == {"learning_rate", "discount", "reward_scale", "optimistic_init", "bins", "epsilon"}


def test_the_key_cache_never_returns_a_stale_result():
    n = 8
    agent = QLearningAgent(n, bin_edges={EWMA: E6}, neighbor_features=[EWMA])
    first, second = _random_obs(n, 1), _random_obs(n, 2)
    expected_first = _reference_keys(first, n, DEFAULT_BINS, {EWMA: E6}, [EWMA])
    expected_second = _reference_keys(second, n, DEFAULT_BINS, {EWMA: E6}, [EWMA])
    for _ in range(3):
        assert agent._keys(first) == expected_first
        assert agent._keys(second) == expected_second
    mutated = first.copy()
    agent._keys(mutated)
    mutated[BAND_FEATURES.index(EWMA)] = 0.99          # modify one value in place after it was cached
    assert agent._keys(mutated) == _reference_keys(mutated, n, DEFAULT_BINS, {EWMA: E6}, [EWMA])
    assert agent._keys(first) == expected_first


# -- shaping ---------------------------------------------------------------------------------------


def _single_step(eff_beta=0.0, cov_beta=0.0, with_observe=True, hits=(3, 4)):
    n = 8
    agent = QLearningAgent(n, eff_beta=eff_beta, cov_beta=cov_beta)
    obs = np.zeros(8 * n + 2)
    obs[3 * NUM_BAND_FEATURES] = 0.25            # band 3 age feature
    obs[4 * NUM_BAND_FEATURES] = 0.75            # band 4 age feature
    obs[7 * n + 3] = obs[7 * n + 4] = 1.0        # tuned block: window (3, 4)
    nxt = np.zeros_like(obs)
    if with_observe:
        agent.observe({"scanned_bands": [3, 4], "detected_bands": list(hits)})
    agent.learn(obs, 3, 1.0, nxt, done=True)
    key = agent._keys(obs)[3]
    return agent.q_table[key]


def test_eff_beta_adds_the_detected_share_but_only_after_observe():
    unshaped = _single_step()
    assert _single_step(eff_beta=4.0, hits=(3, 4)) == pytest.approx(unshaped + 0.15 * 4.0 * 1.0 / 10.0)
    assert _single_step(eff_beta=4.0, hits=(3,)) == pytest.approx(unshaped + 0.15 * 4.0 * 0.5 / 10.0)
    assert _single_step(eff_beta=4.0, with_observe=False) == pytest.approx(unshaped)


def test_cov_beta_adds_the_staleness_of_the_executed_window():
    unshaped = _single_step()
    assert _single_step(cov_beta=2.0) == pytest.approx(unshaped + 0.15 * 2.0 * 0.5 / 10.0)   # mean of 0.25 and 0.75


def test_shaping_is_inactive_at_zero_weights():
    assert _single_step(eff_beta=0.0, cov_beta=0.0) == _single_step()


# -- persistence -----------------------------------------------------------------------------------


def _trained_with_everything():
    agent = QLearningAgent(
        8,
        bin_edges={EWMA: E6},
        neighbor_features=[EWMA],
        neighbor_bin_edges={EWMA: [0.15, 0.4]},
        eff_beta=2.0,
        cov_beta=1.5,
        align_window=True,
    )
    env = EWEnvironment(num_bands=8, duration_steps=60, num_emitters=3, seed=3)
    run_episode(env, agent, seed=3, learn=True, episode=0)
    return agent


def test_save_load_round_trip_keeps_every_option(tmp_path):
    agent = _trained_with_everything()
    path = tmp_path / "q.json"
    agent.save(path)
    loaded = QLearningAgent.load(path)
    assert loaded.q_table == agent.q_table
    assert loaded.hyperparams() == agent.hyperparams()
    # values, not actions: ties between equal values are broken at random by each agent's own generator
    for o, *_ in _rollout()[:20]:
        assert np.array_equal(loaded.q_values(o), agent.q_values(o))
    assert json.loads(path.read_text())["hyperparams"]["neighbor_bin_edges"] == {EWMA: [0.15, 0.4]}


def test_a_file_written_before_these_options_loads_as_a_default_agent(tmp_path):
    original = QLearningAgent(8)
    for obs, action, reward, nxt, _ in _rollout()[:20]:
        original.learn(obs, action, reward, nxt)
    path = tmp_path / "old.json"
    original.save(path)
    payload = json.loads(path.read_text())
    assert set(payload["hyperparams"]) == {"learning_rate", "discount", "reward_scale", "optimistic_init", "bins", "epsilon"}
    loaded = QLearningAgent.load(path)
    assert loaded.q_table == original.q_table
    assert loaded.neighbor_features == () and loaded.bin_edges == {}


def test_table_capacity_counts_every_key_position():
    default = QLearningAgent(8)
    assert default.describe()["table_capacity"] == 3 * 3 * 3 * 2
    mixed = QLearningAgent(8, bin_edges={EWMA: E6}, neighbor_features=[EWMA], neighbor_bin_edges={EWMA: [0.15, 0.4]})
    assert mixed.describe()["table_capacity"] == (6 * 3 * 3 * 2) * 3
    followed = QLearningAgent(8, bin_edges={EWMA: E6}, neighbor_features=[EWMA])
    assert followed.describe()["table_capacity"] == (6 * 3 * 3 * 2) * 6


# -- validation and plumbing ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bin_edges": {"nonsense": [0.1]}},
        {"bin_edges": {EWMA: [0.3, 0.2]}},
        {"bin_edges": {EWMA: [0.2, 0.2]}},
        {"bin_edges": {EWMA: [float("nan")]}},
        {"neighbor_features": ["nonsense"]},
        {"neighbor_features": [EWMA], "neighbor_bin_edges": {AGE: [0.5]}},
        {"eff_beta": -1.0},
        {"cov_beta": -0.1},
    ],
)
def test_invalid_arguments_raise(kwargs):
    with pytest.raises(ValueError):
        QLearningAgent(8, **kwargs)


def test_build_agent_passes_every_option_through():
    agent = build_agent(
        "q_learning",
        8,
        {
            "bin_edges": {EWMA: E6},
            "neighbor_features": [EWMA],
            "neighbor_bin_edges": {EWMA: [0.15, 0.4]},
            "eff_beta": 2.0,
            "cov_beta": 1.0,
            "align_window": True,
        },
    )
    assert isinstance(agent, QLearningAgent)
    assert agent.bin_edges == {EWMA: E6} and agent.neighbor_features == (EWMA,)
    assert agent.hyperparams()["eff_beta"] == 2.0 and agent.align_window


def test_a_short_training_run_with_every_option_on_stays_finite():
    agent = _trained_with_everything()
    assert agent.updates == 60
    assert agent.q_table and all(np.isfinite(v) for v in agent.q_table.values())
    assert all(len(key) == 4 + 1 for key in agent.q_table)
