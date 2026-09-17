"""Common agent interface.

Every policy -- baseline, bandit, Q-Learning, DQN -- implements this, so ``/internal/decide`` and
``/internal/learn`` can dispatch on the ``policy`` field without special-casing (API_CONTRACT.md
Section 4).

Note the split that mirrors the contract: agents *receive* a reward, they never compute one.
Equation 10.1 is the Backend's job in production and ml/environments/reward.py's job during
standalone training.
"""

from __future__ import annotations

import abc
from pathlib import Path

import numpy as np

POLICY_TYPES = ("baseline", "bandit", "q_learning", "dqn", "ppo")


class Agent(abc.ABC):
    """Base class for scan-decision policies."""

    policy_type: str = "baseline"

    def __init__(self, num_bands: int, rng: np.random.Generator | None = None) -> None:
        self.num_bands = num_bands
        self.rng = rng if rng is not None else np.random.default_rng(0)

    @abc.abstractmethod
    def select_action(self, observation: np.ndarray, explore: bool = True) -> int:
        """Choose the next band to tune to."""

    def learn(
        self,
        observation: np.ndarray,
        action: int,
        reward: float,
        next_observation: np.ndarray,
        done: bool = False,
    ) -> None:
        """Consume one (s, a, r, s') transition. No-op for policies that do not learn."""
        return None

    def start_episode(self, episode: int = 0) -> None:
        """Hook for per-episode exploration decay and any per-episode counters."""
        return None

    def end_episode(self, episode: int = 0) -> None:
        return None

    # -- persistence -----------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        raise NotImplementedError(f"{type(self).__name__} does not support checkpointing")

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "Agent":
        raise NotImplementedError(f"{cls.__name__} does not support checkpointing")

    def describe(self) -> dict:
        """Hyperparameters and learned-state summary, for the model registry."""
        return {"policy_type": self.policy_type, "num_bands": self.num_bands}
