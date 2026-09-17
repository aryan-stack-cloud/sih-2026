"""Training pipeline (Ai-ml-1 Level 5).

One entry point, ``train``, covering every algorithm on the Section 10.1 ladder. Tabular agents
learn online over whole episodes; SB3 agents train inside ``model.learn()``. Both then get the
same held-out evaluation so their numbers are directly comparable.

Training and evaluation seeds are disjoint by construction: training draws from ``seed + 1000``
upward, evaluation uses the scenario's own ``seed_range``. Reporting a policy on the seeds it was
fitted on would make every algorithm look good and would tell us nothing about the next
simulation.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from ml.agents.base import Agent
from ml.agents.factory import build_agent
from ml.environments.environment import make_env
from ml.evaluation.evaluator import EpisodeMetrics, aggregate
from ml.evaluation.runner import run_episode
from ml.utils.config import episode_seeds, load_hyperparams, load_scenario
from ml.utils.logging import get_logger

log = get_logger(__name__)

ProgressCallback = Callable[[float, dict], None]


def train(
    algorithm: str,
    scenario: str | dict,
    hyperparams: dict[str, Any] | None = None,
    episode_count: int | None = None,
    seed_range: tuple[int, int] | None = None,
    eval_episodes: int | None = None,
    progress: ProgressCallback | None = None,
) -> dict:
    """Train one policy on one scenario and evaluate it on held-out seeds.

    Mirrors the ``/internal/train`` request body (API_CONTRACT.md Section 4):
    ``{algorithm, scenario, hyperparams, episode_count, seed_range}``.
    """
    cfg = load_scenario(scenario) if isinstance(scenario, str) else dict(scenario)
    defaults = {k: v for k, v in load_hyperparams(algorithm).items() if not k.startswith("_")}
    merged = {**defaults, **(hyperparams or {})}
    merged.pop("algorithm", None)

    episodes = int(
        episode_count if episode_count is not None else merged.pop("train_episodes", 20)
    )
    merged.pop("train_episodes", None)

    if seed_range is not None:
        train_seeds = list(range(int(seed_range[0]), int(seed_range[1])))
        if episode_count is not None:
            train_seeds = train_seeds[:episodes] or train_seeds
    else:
        base = int(cfg.get("seed", 42))
        train_seeds = [base + 1000 + i for i in range(episodes)]

    agent = build_agent(algorithm, cfg["bands"], merged)
    started = time.perf_counter()

    # Training is only part of the job: evaluation runs >= 20 episodes afterwards (Section 13)
    # and can take longer than the training itself. Reporting 1.0 at the end of training left the
    # job sitting at "100%, still running" for the whole evaluation, which is exactly the shape
    # of progress bar the Frontend would render as a hang.
    TRAIN_FRACTION = 0.8

    def train_progress(fraction: float, detail: dict | None = None) -> None:
        if progress:
            progress(fraction * TRAIN_FRACTION, {"phase": "training", **(detail or {})})

    if algorithm in ("dqn", "ppo"):
        train_curve = _train_deep(agent, cfg, train_seeds, merged, train_progress)
    else:
        train_curve = _train_tabular(agent, cfg, train_seeds, train_progress)

    train_seconds = time.perf_counter() - started

    def eval_progress(fraction: float, detail: dict | None = None) -> None:
        if progress:
            progress(
                TRAIN_FRACTION + fraction * (1.0 - TRAIN_FRACTION),
                {"phase": "evaluating", **(detail or {})},
            )

    eval_progress(0.0, {"episode": 0})
    summary = evaluate(agent, cfg, eval_episodes, progress=eval_progress)
    summary.update(
        {
            "algorithm": algorithm,
            "train_episodes": len(train_curve),
            "train_seeds": [train_seeds[0], train_seeds[-1]] if train_seeds else [],
            "train_seconds": round(train_seconds, 3),
            "hyperparams": merged,
            "reward_weights": cfg.get("reward_weights", {}),
        }
    )
    log.info(
        "training complete",
        extra={"algorithm": algorithm, "scenario_id": cfg.get("scenario_id"), "pd": summary["pd"]},
    )
    return {"agent": agent, "summary": summary, "train_curve": train_curve}


def _train_tabular(
    agent: Agent, cfg: dict, seeds: list[int], progress: ProgressCallback | None
) -> list[float]:
    curve: list[float] = []
    for i, seed in enumerate(seeds):
        env = make_env(cfg, seed=seed)
        m = run_episode(env, agent, seed=seed, learn=True, episode=i)
        curve.append(m.cumulative_reward)
        if progress:
            progress((i + 1) / len(seeds), {"episode": i + 1, "reward": m.cumulative_reward})
    return curve


def _train_deep(
    agent: Agent, cfg: dict, seeds: list[int], merged: dict, progress: ProgressCallback | None
) -> list[float]:
    """SB3 path. Trains on one seed's environment for total_timesteps.

    A single environment is intentional at this level: the point of Level 9 is to show DQN/PPO
    working through the unchanged contract, not to build a distributed training rig. Widening to
    a VecEnv over several seeds is the obvious next step if the deep agents are ever promoted.
    """
    from stable_baselines3.common.callbacks import BaseCallback

    total = int(merged.get("total_timesteps", 50_000))

    class _Progress(BaseCallback):
        def _on_step(self) -> bool:
            if progress and self.num_timesteps % 1000 == 0:
                progress(min(1.0, self.num_timesteps / total), {"timesteps": self.num_timesteps})
            return True

    env = make_env(cfg, seed=seeds[0] if seeds else cfg.get("seed", 42))
    agent.fit(env, total_timesteps=total, seed=seeds[0] if seeds else None, callback=_Progress())
    return [float(total)]


def evaluate(
    agent: Agent,
    scenario: str | dict,
    episodes: int | None = None,
    seeds: list[int] | None = None,
    progress: ProgressCallback | None = None,
) -> dict:
    """Score a trained agent on a scenario's evaluation seeds.

    Online learning stays enabled for the agents that support it, because that is how they run in
    deployment -- the Backend calls ``/internal/learn`` after every step. It is a no-op for
    ``baseline`` and for the SB3 agents.
    """
    cfg = load_scenario(scenario) if isinstance(scenario, str) else dict(scenario)
    seed_list = list(seeds) if seeds is not None else episode_seeds(cfg, episodes)

    per_episode: list[EpisodeMetrics] = []
    latencies: list[float] = []
    for i, seed in enumerate(seed_list):
        env = make_env(cfg, seed=seed)
        started = time.perf_counter()
        per_episode.append(
            run_episode(env, agent, seed=seed, learn=True, explore=False, episode=i)
        )
        latencies.append((time.perf_counter() - started) / max(1, env.t) * 1000.0)
        if progress:
            progress((i + 1) / len(seed_list), {"episode": i + 1, "of": len(seed_list)})

    summary = aggregate(per_episode)
    summary["policy"] = agent.policy_type
    summary["scenario_id"] = cfg.get("scenario_id")
    summary["eval_seeds"] = seed_list
    # Per-step decision latency, the NFR-002 budget (< 50 ms bandit/Q-Learning, < 150 ms DQN).
    summary["decision_latency_ms_mean"] = round(sum(latencies) / len(latencies), 4)
    return summary
