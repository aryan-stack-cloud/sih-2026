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

import gymnasium as gym

from ml.agents.base import Agent
from ml.agents.factory import build_agent
from ml.environments.environment import make_env
from ml.features.periodicity_provider import (
    serving_periodicity_provider,
    serving_periodicity_source,
)
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
    if algorithm in ("dqn", "ppo"):
        merged = _scale_for_band_count(algorithm, merged, cfg["bands"])

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
        train_curve = _train_deep(
            agent, cfg, train_seeds, merged, train_progress, explicit_seeds=seed_range is not None
        )
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
    source = serving_periodicity_source()
    if source != "ai-ml-2":
        log.warning(
            "trained without Ai-ml-2's estimator; the served periodicity features will differ",
            extra={"algorithm": algorithm, "periodicity_source": source},
        )
    summary.update(
        {
            "algorithm": algorithm,
            "train_episodes": len(train_curve),
            "train_seeds": [train_seeds[0], train_seeds[-1]] if train_seeds else [],
            "train_seconds": round(train_seconds, 3),
            # Persisted into the registry record through hyperparams, next to what it explains.
            "hyperparams": {**merged, "periodicity_source": source},
            "periodicity_source": source,
            "reward_weights": cfg.get("reward_weights", {}),
        }
    )
    log.info(
        "training complete",
        extra={"algorithm": algorithm, "scenario_id": cfg.get("scenario_id"), "pd": summary["pd"]},
    )
    return {"agent": agent, "summary": summary, "train_curve": train_curve}


def _scale_for_band_count(algorithm: str, hyperparams: dict, num_bands: int) -> dict:
    """Scale DQN/PPO's exploration budget with the action-space size.

    Unlike bandit/Q-Learning -- whose optimistic per-band init forces every band to be tried at
    least once, by construction -- DQN/PPO explore with a fixed epsilon/entropy schedule over a
    fixed total_timesteps, regardless of num_bands. At reference_bands the schedule was tuned to
    work; at 2x the bands, each action gets roughly half the exploration hits, which was observed
    collapsing the trained policy onto 1-2 bands (near-0 Pd on 32-band scenarios E/F). Scale
    linearly against the reference band count so smaller scenarios are unaffected.
    """
    reference = float(hyperparams.get("reference_bands", 16))
    scale = max(1.0, num_bands / reference)
    scaled = dict(hyperparams)
    scaled.pop("reference_bands", None)
    if "total_timesteps" in scaled:
        scaled["total_timesteps"] = int(round(scaled["total_timesteps"] * scale))
    if algorithm == "dqn" and "exploration_fraction" in scaled:
        scaled["exploration_fraction"] = min(0.6, scaled["exploration_fraction"] * scale)
    if algorithm == "ppo" and "ent_coef" in scaled:
        scaled["ent_coef"] = min(0.05, scaled["ent_coef"] * scale)
    return scaled


def _serving_env(cfg: dict, seed: int):
    """An environment whose periodicity features are the ones a served model will receive.

    Training and evaluation both use Ai-ml-2's estimator (see ServicePeriodicityProvider): a
    model is only as good as the features it is served, not the ones it happened to train on.
    """
    return make_env(cfg, seed=seed, periodicity_provider=serving_periodicity_provider())


def _train_tabular(
    agent: Agent, cfg: dict, seeds: list[int], progress: ProgressCallback | None
) -> list[float]:
    curve: list[float] = []
    for i, seed in enumerate(seeds):
        env = _serving_env(cfg, seed)
        m = run_episode(env, agent, seed=seed, learn=True, episode=i)
        curve.append(m.cumulative_reward)
        if progress:
            progress((i + 1) / len(seeds), {"episode": i + 1, "reward": m.cumulative_reward})
    return curve


class _SeedCyclingEnv(gym.Wrapper):
    """Gives every SB3 training episode its own spectrum.

    SB3 seeds an environment once, on its first reset, and auto-resets with ``seed=None`` after
    that -- and ``EWEnvironment.reset(seed=None)`` deliberately replays the same seed, so the same
    emitter layout and noise came back every episode. DQN/PPO were therefore trained on ONE
    spectrum realisation replayed 25-150 times: they memorised which band paid in that layout and
    collapsed onto a single constant action (every one of 600 served decisions was band 12),
    scoring below the round-robin sweep on any other seed. The tabular agents never had this
    problem because ``_train_tabular`` builds a fresh environment per seed.
    """

    def __init__(self, env: gym.Env, seeds: list[int]) -> None:
        super().__init__(env)
        self._seeds = list(seeds)
        self._episode = 0

    def reset(self, *, seed=None, options=None):
        episode_seed = self._seeds[self._episode % len(self._seeds)]
        self._episode += 1
        return self.env.reset(seed=episode_seed, options=options)


def deep_training_seeds(cfg: dict, seeds: list[int], total_timesteps: int) -> list[int]:
    """One distinct training seed per episode SB3 will actually run.

    An explicit ``seed_range`` is respected (and cycled if SB3 runs more episodes than it holds);
    otherwise the default ``seed + 1000 + i`` stream is extended far enough that no layout repeats.
    Either way the stream stays disjoint from the scenario's evaluation ``seed_range``.
    """
    needed = -(-int(total_timesteps) // max(1, int(cfg["duration_steps"]))) + 1
    if len(seeds) >= needed:
        return list(seeds)
    base = seeds[0] if seeds else int(cfg.get("seed", 42)) + 1000
    extended = list(seeds)
    i = len(extended)
    while len(extended) < needed:
        extended.append(base + i)
        i += 1
    return extended


def _train_deep(
    agent: Agent,
    cfg: dict,
    seeds: list[int],
    merged: dict,
    progress: ProgressCallback | None,
    explicit_seeds: bool = False,
) -> list[float]:
    """SB3 path: one environment whose every episode is a different seed's spectrum."""
    from stable_baselines3.common.callbacks import BaseCallback

    total = int(merged.get("total_timesteps", 50_000))

    class _Progress(BaseCallback):
        def _on_step(self) -> bool:
            if progress and self.num_timesteps % 1000 == 0:
                progress(min(1.0, self.num_timesteps / total), {"timesteps": self.num_timesteps})
            return True

    episode_seeds = list(seeds) if explicit_seeds and seeds else deep_training_seeds(cfg, seeds, total)
    env = _SeedCyclingEnv(_serving_env(cfg, episode_seeds[0]), episode_seeds)
    agent.fit(env, total_timesteps=total, seed=episode_seeds[0], callback=_Progress())
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
        env = _serving_env(cfg, seed)
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
