"""Shared exploration/exploitation strategies (Ai-ml-1 README, ml/algorithms/).

PRD Section 10.4: epsilon-greedy for bandit and Q-Learning, with epsilon decayed per episode.
Keeping the schedules here rather than inside each agent means the bandit and the Q-Learner
decay identically, so a difference between them is a difference in the algorithm rather than in
how hard each one happened to explore.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class EpsilonSchedule:
    """Per-episode epsilon decay.

    ``mode="exponential"``  eps = max(end, start * decay**episode)
    ``mode="linear"``       eps falls from start to end over ``decay_episodes`` episodes
    """

    start: float = 1.0
    end: float = 0.05
    decay: float = 0.92
    decay_episodes: int = 50
    mode: str = "exponential"

    def __post_init__(self) -> None:
        if not 0.0 <= self.end <= self.start <= 1.0:
            raise ValueError("require 0 <= end <= start <= 1")
        if self.mode not in ("exponential", "linear", "constant"):
            raise ValueError("mode must be exponential, linear or constant")

    def value(self, episode: int) -> float:
        if self.mode == "constant":
            return self.start
        if self.mode == "linear":
            frac = min(1.0, episode / max(1, self.decay_episodes))
            return float(self.start + (self.end - self.start) * frac)
        return float(max(self.end, self.start * (self.decay ** episode)))


def epsilon_greedy(
    values: np.ndarray, epsilon: float, rng: np.random.Generator, explore: bool = True
) -> int:
    """Argmax with probability 1-eps, uniform random otherwise.

    Ties in the argmax are broken uniformly at random rather than by index. With optimistic
    initialisation every arm starts tied, and np.argmax would otherwise always return band 0 --
    an exploration bug that looks like a policy that refuses to move.
    """
    if explore and rng.random() < epsilon:
        return int(rng.integers(0, len(values)))
    best = np.flatnonzero(values == values.max())
    return int(best[0] if best.size == 1 else rng.choice(best))
