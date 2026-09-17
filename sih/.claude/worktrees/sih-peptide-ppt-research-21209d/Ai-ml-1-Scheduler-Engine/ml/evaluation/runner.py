"""Episode runner shared by training, evaluation and the comparison scripts.

One place owns the (reset -> select_action -> step -> learn) loop so that a policy is scored the
same way whether it is being trained, evaluated, or compared against the baseline. The seed list
comes from the scenario config, so every policy sees the identical sequence of spectra.
"""

from __future__ import annotations

import time
from typing import Callable, Sequence

from ml.agents.base import Agent
from ml.environments.environment import EWEnvironment, make_env
from ml.evaluation.evaluator import EpisodeMetrics, aggregate, score_episode
from ml.utils.config import episode_seeds


def run_episode(
    env: EWEnvironment,
    agent: Agent,
    seed: int,
    learn: bool = False,
    explore: bool | None = None,
    episode: int = 0,
) -> EpisodeMetrics:
    """Run one full episode and score it. ``learn=False`` gives a clean evaluation pass."""
    if explore is None:
        explore = learn

    obs, _ = env.reset(seed=seed)
    agent.start_episode(episode)

    while True:
        action = agent.select_action(obs, explore=explore)
        next_obs, reward, terminated, truncated, _ = env.step(action)
        if learn:
            # Mirrors /internal/learn: the agent is handed a reward, it does not compute one.
            agent.learn(obs, action, reward, next_obs, done=terminated or truncated)
        obs = next_obs
        if terminated or truncated:
            break

    agent.end_episode(episode)
    return score_episode(env.history, env.ground_truth, env.num_bands)


def run_policy(
    scenario: dict,
    agent_factory: Callable[[int], Agent],
    episodes: int | None = None,
    learn: bool = False,
    seeds: Sequence[int] | None = None,
    env_factory: Callable[[dict, int], EWEnvironment] | None = None,
) -> dict:
    """Run a policy across a scenario's episode seeds and aggregate the results."""
    seed_list = list(seeds) if seeds is not None else episode_seeds(scenario, episodes)
    env_factory = env_factory or (lambda cfg, s: make_env(cfg, seed=s))

    agent = agent_factory(scenario["bands"])
    per_episode: list[EpisodeMetrics] = []

    started = time.perf_counter()
    for i, seed in enumerate(seed_list):
        env = env_factory(scenario, seed)
        per_episode.append(run_episode(env, agent, seed=seed, learn=learn, episode=i))
    elapsed = time.perf_counter() - started

    summary = aggregate(per_episode)
    summary["policy"] = agent.policy_type
    summary["scenario_id"] = scenario.get("scenario_id")
    summary["seeds"] = seed_list
    summary["wall_seconds"] = round(elapsed, 3)
    return {"summary": summary, "episodes": per_episode, "agent": agent}


def train_then_evaluate(
    scenario: dict,
    agent_factory: Callable[[int], Agent],
    train_episodes: int,
    eval_episodes: int | None = None,
    env_factory: Callable[[dict, int], EWEnvironment] | None = None,
) -> dict:
    """Train on one seed block, then evaluate greedily on the scenario's held-out eval seeds.

    Training and evaluation seeds are disjoint so the reported numbers are not the numbers the
    policy was fitted on -- Section 13 asks for statistical stability, not memorisation.
    """
    base = int(scenario.get("seed", 42))
    train_seeds = [base + 1000 + i for i in range(train_episodes)]
    eval_seed_list = episode_seeds(scenario, eval_episodes)

    agent = agent_factory(scenario["bands"])
    env_factory = env_factory or (lambda cfg, s: make_env(cfg, seed=s))

    started = time.perf_counter()
    train_curve: list[float] = []
    for i, seed in enumerate(train_seeds):
        env = env_factory(scenario, seed)
        m = run_episode(env, agent, seed=seed, learn=True, episode=i)
        train_curve.append(m.cumulative_reward)
    train_seconds = time.perf_counter() - started

    # Evaluation runs with online learning ON and exploration OFF, because that is exactly what
    # deployment does: the Backend calls /internal/decide and then /internal/learn on every step
    # of a live simulation (API_CONTRACT.md Section 4). A learned policy that was frozen at the
    # end of training would be scored on a mode it never actually runs in. Exploration stays off
    # so the measured numbers are the policy's own, and so the run is deterministic given a seed
    # (NFR-006) -- the optimistic per-band init supplies the early sweep instead of randomness.
    per_episode: list[EpisodeMetrics] = []
    for i, seed in enumerate(eval_seed_list):
        env = env_factory(scenario, seed)
        per_episode.append(
            run_episode(env, agent, seed=seed, learn=True, explore=False, episode=i)
        )

    summary = aggregate(per_episode)
    summary["policy"] = agent.policy_type
    summary["scenario_id"] = scenario.get("scenario_id")
    summary["seeds"] = eval_seed_list
    summary["train_episodes"] = train_episodes
    summary["train_seconds"] = round(train_seconds, 3)
    return {
        "summary": summary,
        "episodes": per_episode,
        "agent": agent,
        "train_curve": train_curve,
    }
