"""Policy factory -- one place that maps a ``policy_type`` string to an agent.

``/internal/decide`` and ``/internal/train`` both dispatch on the ``policy`` / ``algorithm``
field of API_CONTRACT.md Section 4, and the CLI scripts take the same names. Centralising the
mapping means the contract's ``policy_type`` enum is honoured identically everywhere.
"""

from __future__ import annotations

from typing import Any, Callable

from ml.agents.base import POLICY_TYPES, Agent
from ml.agents.bandit_agent import BanditAgent
from ml.agents.baseline_scanner import BaselineScanner
from ml.agents.q_learning_agent import QLearningAgent
from ml.algorithms.exploration import EpsilonSchedule
from ml.utils.config import load_hyperparams

# dqn/ppo are imported lazily: Stable-Baselines3 and torch are a heavy import, and the V2 agents
# are gated behind the MVP result (Ai-ml-1 Level 9), so most runs never need them.
LEARNING_POLICIES = ("bandit", "q_learning", "dqn", "ppo")


def _strip_meta(cfg: dict) -> dict:
    return {k: v for k, v in cfg.items() if not k.startswith("_") and k != "algorithm"}


def build_agent(
    policy: str,
    num_bands: int,
    hyperparams: dict[str, Any] | None = None,
    rng=None,
    **kwargs,
) -> Agent:
    """Build an agent for a contract ``policy_type``.

    ``hyperparams`` overrides the algorithm's ml/configs/<policy>.yaml defaults.
    """
    policy = str(policy).lower()
    if policy not in POLICY_TYPES:
        raise ValueError(f"unknown policy {policy!r}; expected one of {POLICY_TYPES}")

    cfg = _strip_meta(load_hyperparams(policy))
    cfg.update(_strip_meta(hyperparams or {}))
    cfg.update(kwargs)

    if policy == "baseline":
        return BaselineScanner(
            num_bands,
            mode=cfg.get("mode", "round_robin"),
            stride=cfg.get("stride", 1),
            band_order=cfg.get("band_order"),
            rng=rng,
        )

    if policy in ("bandit", "q_learning"):
        cfg.pop("train_episodes", None)
        eps = EpsilonSchedule(**cfg.pop("epsilon", {}))
        cls = BanditAgent if policy == "bandit" else QLearningAgent
        return cls(num_bands, epsilon=eps, rng=rng, **cfg)

    from ml.agents.dqn_agent import DeepRLAgent  # noqa: PLC0415 - deliberate lazy import

    return DeepRLAgent(num_bands, algorithm=policy, rng=rng, **cfg)


def agent_factory(
    policy: str, hyperparams: dict[str, Any] | None = None, **kwargs
) -> Callable[[int], Agent]:
    """Curried form, for the runners which build one agent per scenario."""
    return lambda num_bands: build_agent(policy, num_bands, hyperparams, **kwargs)
