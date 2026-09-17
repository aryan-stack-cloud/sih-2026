"""Action space (ML-002 / API_CONTRACT.md Section 4).

MVP and V1 -- bandit and Q-Learning -- use ``{"next_band": int}``, so the Gymnasium space is
``Discrete(N)``.

Instantaneous bandwidth does not change that. The receiver observes K bands per step, but the
action names only the *start* of the contiguous K-band block (PRD Section 9.2, "K bands
observable per step"). Encoding the block as a start index rather than as a set of K bands keeps
the action space Discrete(N) instead of C(N, K), which is what makes a tabular bandit or
Q-table tractable at N = 32 -- and it is the shape the contract already specifies.

V2 -- DQN/PPO with dwell-time control -- switches to ``MultiDiscrete([N, len(dwell_options)])``,
populating the contract's optional ``dwell_time`` field. Ai-ml-1 README Level 9 gates this behind
the MVP acceptance result, so it stays off by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import gymnasium as gym


@dataclass
class ActionSpaceSpec:
    """Describes the action space and converts between agent actions and contract actions."""

    num_bands: int
    dwell_options: tuple[int, ...] = field(default_factory=tuple)

    @property
    def includes_dwell(self) -> bool:
        return bool(self.dwell_options)

    def to_gym(self) -> gym.Space:
        if self.includes_dwell:
            return gym.spaces.MultiDiscrete([self.num_bands, len(self.dwell_options)])
        return gym.spaces.Discrete(self.num_bands)

    def decode(self, action) -> tuple[int, int | None]:
        """Agent action -> ``(next_band, dwell_time)``; dwell is None in the MVP space."""
        if self.includes_dwell:
            band, dwell_idx = int(action[0]), int(action[1])
            return band % self.num_bands, int(self.dwell_options[dwell_idx])
        return int(action) % self.num_bands, None

    def to_contract(self, action) -> dict:
        """Agent action -> the ``action`` object of ``/internal/decide``."""
        next_band, dwell = self.decode(action)
        out: dict = {"next_band": next_band}
        if dwell is not None:
            out["dwell_time"] = dwell
        return out

    def from_contract(self, action: dict):
        """The contract's ``action`` object -> an agent action."""
        next_band = int(action["next_band"]) % self.num_bands
        if not self.includes_dwell:
            return next_band
        dwell = int(action.get("dwell_time", self.dwell_options[0]))
        if dwell not in self.dwell_options:
            raise ValueError(f"dwell_time {dwell} not in configured options {self.dwell_options}")
        return [next_band, self.dwell_options.index(dwell)]
