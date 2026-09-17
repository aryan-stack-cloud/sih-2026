"""Tabular Q-Learning -- the V1 escalation (PRD Section 10.1, Ai-ml-1 Level 7).

What this buys over the bandit: the bandit predicts the *immediate* payoff of a band, so it
cannot represent "this band is worth nothing right now, but visiting it now sets up a detection
two steps from now". Q-Learning bootstraps, so it can.

What it costs: a table. The raw state is 8N + 2 continuous features, which is not tabular, so the
state must be discretised. The PRD's own mitigation for training instability is "small
state/action space for MVP" (Section 24), and this follows it literally:

    per-band key  = (ewma bin, age bin, periodicity-phase bin, periodicity-confidence bin)

The table is keyed on the *chosen band's own* discretised features, not on the joint state of
all N bands -- a joint table would have bins^(4N) entries and never be visited twice. So the
Q-value is Q(band-context, "tune here"), and bootstrapping happens against the best available
band context on the next step. This keeps the table at bins^4 entries per action-slot: visitable
within tens of episodes, and still able to express temporal set-up that the bandit cannot.

Reproducibility (NFR-006, Level 8): the table is an ordinary dict keyed by integer tuples and
updated in a fixed order, so identical seed plus identical config gives an identical table.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ml.agents.base import Agent
from ml.algorithms.exploration import EpsilonSchedule, epsilon_greedy
from ml.environments.state import BAND_FEATURES, NUM_BAND_FEATURES

DEFAULT_BINS = {
    "recent_detection_rate_ewma": 3,
    "time_since_last_scan": 3,
    "periodicity_phase": 3,
    "periodicity_confidence": 2,
}


class QLearningAgent(Agent):
    """Tabular Q-Learning over discretised per-band context."""

    policy_type = "q_learning"

    def __init__(
        self,
        num_bands: int,
        learning_rate: float = 0.15,
        discount: float = 0.9,
        reward_scale: float = 10.0,
        optimistic_init: float = 0.5,
        bins: dict[str, int] | None = None,
        epsilon: EpsilonSchedule | None = None,
        rng: np.random.Generator | None = None,
    ) -> None:
        super().__init__(num_bands, rng)
        self.learning_rate = float(learning_rate)
        self.discount = float(discount)
        self.reward_scale = float(reward_scale)
        self.optimistic_init = float(optimistic_init)
        self.bins = dict(bins or DEFAULT_BINS)
        self.epsilon_schedule = epsilon or EpsilonSchedule()

        self._feature_index = {name: i for i, name in enumerate(BAND_FEATURES)}
        missing = set(self.bins) - set(self._feature_index)
        if missing:
            raise ValueError(f"cannot bin unknown features {sorted(missing)}")

        self.q_table: dict[tuple[int, ...], float] = {}
        self.visit_counts: dict[tuple[int, ...], int] = {}
        self.epsilon = self.epsilon_schedule.value(0)
        self.updates = 0

    # -- discretisation -------------------------------------------------------------------

    def _band_matrix(self, observation: np.ndarray) -> np.ndarray:
        n = self.num_bands
        return np.asarray(
            observation[: NUM_BAND_FEATURES * n], dtype=np.float64
        ).reshape(n, NUM_BAND_FEATURES)

    def _keys(self, observation: np.ndarray) -> list[tuple[int, ...]]:
        """One discretised context key per band. Features are already normalised to [0, 1]."""
        bands = self._band_matrix(observation)
        keys: list[tuple[int, ...]] = []
        for b in range(self.num_bands):
            key = []
            for name in sorted(self.bins):
                nbins = self.bins[name]
                value = bands[b, self._feature_index[name]]
                key.append(int(min(nbins - 1, max(0, int(value * nbins)))))
            keys.append(tuple(key))
        return keys

    def q_values(self, observation: np.ndarray) -> np.ndarray:
        keys = self._keys(observation)
        return np.array(
            [self.q_table.get(k, self.optimistic_init) for k in keys], dtype=np.float64
        )

    # -- Agent API ------------------------------------------------------------------------

    def start_episode(self, episode: int = 0) -> None:
        # Unlike the bandit's per-band bias, the Q-table is keyed on *context*, not on band
        # identity -- "a band that is overdue and periodically confident" means the same thing
        # in every simulation. So it carries across episodes and is the transferable artefact.
        self.epsilon = self.epsilon_schedule.value(episode)

    def select_action(self, observation: np.ndarray, explore: bool = True) -> int:
        return epsilon_greedy(self.q_values(observation), self.epsilon, self.rng, explore)

    def learn(
        self,
        observation: np.ndarray,
        action: int,
        reward: float,
        next_observation: np.ndarray,
        done: bool = False,
    ) -> None:
        key = self._keys(observation)[action]
        current = self.q_table.get(key, self.optimistic_init)
        target = float(reward) / self.reward_scale
        if not done:
            target += self.discount * float(self.q_values(next_observation).max())
        self.q_table[key] = current + self.learning_rate * (target - current)
        self.visit_counts[key] = self.visit_counts.get(key, 0) + 1
        self.updates += 1

    # -- persistence ----------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "num_bands": self.num_bands,
            "hyperparams": self.hyperparams(),
            # Sorted so the serialised table is byte-identical for an identical trained table.
            "q_table": {",".join(map(str, k)): v for k, v in sorted(self.q_table.items())},
            "visit_counts": {
                ",".join(map(str, k)): v for k, v in sorted(self.visit_counts.items())
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "QLearningAgent":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        hp = dict(payload["hyperparams"])
        eps = EpsilonSchedule(**hp.pop("epsilon"))
        agent = cls(num_bands=int(payload["num_bands"]), epsilon=eps, **hp, **kwargs)
        agent.q_table = {
            tuple(int(x) for x in k.split(",")): float(v) for k, v in payload["q_table"].items()
        }
        agent.visit_counts = {
            tuple(int(x) for x in k.split(",")): int(v)
            for k, v in payload.get("visit_counts", {}).items()
        }
        agent.epsilon = eps.end
        return agent

    def hyperparams(self) -> dict:
        return {
            "learning_rate": self.learning_rate,
            "discount": self.discount,
            "reward_scale": self.reward_scale,
            "optimistic_init": self.optimistic_init,
            "bins": dict(self.bins),
            "epsilon": {
                "start": self.epsilon_schedule.start,
                "end": self.epsilon_schedule.end,
                "decay": self.epsilon_schedule.decay,
                "decay_episodes": self.epsilon_schedule.decay_episodes,
                "mode": self.epsilon_schedule.mode,
            },
        }

    def describe(self) -> dict:
        return {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "hyperparams": self.hyperparams(),
            "updates": int(self.updates),
            "epsilon": float(self.epsilon),
            "table_size": len(self.q_table),
            "table_capacity": int(np.prod([self.bins[k] for k in sorted(self.bins)])),
        }
