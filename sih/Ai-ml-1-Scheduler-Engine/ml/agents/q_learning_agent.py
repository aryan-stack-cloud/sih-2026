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
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

from ml.agents.base import Agent, align_window_start
from ml.agents.shaping import RewardShaping
from ml.algorithms.exploration import EpsilonSchedule, epsilon_greedy
from ml.environments.state import BAND_FEATURES, NUM_BAND_FEATURES

DEFAULT_BINS = {
    "recent_detection_rate_ewma": 3,
    "time_since_last_scan": 3,
    "periodicity_phase": 3,
    "periodicity_confidence": 2,
}

# A feature that is binned by neighbour only (not in ``bins`` and without edges) gets this many uniform bins.
FALLBACK_UNIFORM_BINS = 3


class QLearningAgent(Agent):
    """Tabular Q-Learning over discretised per-band context.

    Opt-in refinements, all off by default (a default agent is byte-for-byte the original):

    * ``bin_edges`` -- non-uniform bins for named features (``len(edges) + 1`` bins, ``np.searchsorted(edges, v, "right")``).
      A detection EWMA of 0.2 (one hit) and 0.0 (never hit) share a bin under three uniform bins; edges at 0.05, 0.15, ... do not.
    * ``neighbor_features`` / ``neighbor_bin_edges`` -- the NEXT band's value of these features joins the key, because the
      receiver window of K = 2 bands starting at ``b`` also covers band ``b + 1``.
    * ``eff_beta`` / ``cov_beta`` -- the agent-side shaping terms of ml/agents/shaping.py.
    """

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
        align_window: bool = False,
        bin_edges: Mapping[str, Sequence[float]] | None = None,
        neighbor_features: Sequence[str] = (),
        neighbor_bin_edges: Mapping[str, Sequence[float]] | None = None,
        eff_beta: float = 0.0,
        cov_beta: float = 0.0,
    ) -> None:
        super().__init__(num_bands, rng)
        self.learning_rate = float(learning_rate)
        self.discount = float(discount)
        self.reward_scale = float(reward_scale)
        self.optimistic_init = float(optimistic_init)
        self.bins = dict(bins or DEFAULT_BINS)
        self.epsilon_schedule = epsilon or EpsilonSchedule()
        self.align_window = bool(align_window)

        self._feature_index = {name: i for i, name in enumerate(BAND_FEATURES)}
        self.bin_edges = self._clean_edges(bin_edges, "bin_edges")
        self.neighbor_features = tuple(str(f) for f in neighbor_features)
        self.neighbor_bin_edges = self._clean_edges(neighbor_bin_edges, "neighbor_bin_edges")
        missing = (set(self.bins) | set(self.bin_edges) | set(self.neighbor_features)) - set(self._feature_index)
        if missing:
            raise ValueError(f"cannot bin unknown features {sorted(missing)}")
        stray = set(self.neighbor_bin_edges) - set(self.neighbor_features)
        if stray:
            raise ValueError(f"neighbor_bin_edges names features that are not neighbour features: {sorted(stray)}")
        if float(eff_beta) < 0.0 or float(cov_beta) < 0.0:
            raise ValueError("eff_beta and cov_beta must be non-negative")
        self._shaping = RewardShaping(eff_beta, cov_beta)
        # Features of the own band in the key, in key order (sorted by name, as before).
        self._key_features = sorted(set(self.bins) | set(self.bin_edges))
        self._key_cache: dict[bytes, list[tuple[int, ...]]] = {}

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

    @staticmethod
    def _clean_edges(edges: Mapping[str, Sequence[float]] | None, what: str) -> dict[str, list[float]]:
        """Validated copy: every feature's thresholds must be finite and strictly ascending."""
        out: dict[str, list[float]] = {}
        for name, values in (edges or {}).items():
            arr = np.asarray(list(values), dtype=np.float64)
            if arr.ndim != 1 or not np.all(np.isfinite(arr)) or (arr.size > 1 and not np.all(np.diff(arr) > 0)):
                raise ValueError(f"{what}[{name!r}] must be finite and strictly ascending, got {list(values)!r}")
            out[str(name)] = [float(x) for x in arr]
        return out

    def _bin_column(self, name: str, values: np.ndarray, edges: Sequence[float] | None) -> np.ndarray:
        """Bin index of every band's value of one feature: thresholds if given, else uniform over ``bins`` (3 if unlisted)."""
        if edges is not None:
            return np.searchsorted(np.asarray(edges, dtype=np.float64), values, side="right")
        nbins = self.bins.get(name, FALLBACK_UNIFORM_BINS)
        return np.minimum(nbins - 1, np.maximum(0, (values * nbins).astype(np.int64)))

    def _keys(self, observation: np.ndarray) -> list[tuple[int, ...]]:
        """One discretised context key per band. Features are already normalised to [0, 1].

        The key is the band's own bins (feature names sorted) followed by the next band's bins of the neighbour features.
        ``select_action``, ``learn(s)`` and ``learn(s')`` keep asking for the keys of the same vector, so the last two are cached
        on the exact bytes of the observation.
        """
        raw = np.asarray(observation).tobytes()
        cached = self._key_cache.get(raw)
        if cached is not None:
            return cached
        bands = self._band_matrix(observation)
        columns = [
            self._bin_column(name, bands[:, self._feature_index[name]], self.bin_edges.get(name))
            for name in self._key_features
        ]
        for name in self.neighbor_features:
            edges = self.neighbor_bin_edges.get(name, self.bin_edges.get(name))
            columns.append(np.roll(self._bin_column(name, bands[:, self._feature_index[name]], edges), -1))
        keys = list(map(tuple, np.stack(columns, axis=1).tolist()))
        if len(self._key_cache) >= 2:
            self._key_cache.pop(next(iter(self._key_cache)))
        self._key_cache[raw] = keys
        return keys

    def _key_bin_counts(self) -> list[int]:
        """Number of bins at every key position (own features, then neighbour features)."""
        def nbins(name: str, edges: Sequence[float] | None) -> int:
            return len(edges) + 1 if edges is not None else self.bins.get(name, FALLBACK_UNIFORM_BINS)

        own = [nbins(name, self.bin_edges.get(name)) for name in self._key_features]
        near = [nbins(name, self.neighbor_bin_edges.get(name, self.bin_edges.get(name))) for name in self.neighbor_features]
        return own + near

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
        chosen = epsilon_greedy(self.q_values(observation), self.epsilon, self.rng, explore)
        if self.align_window:
            return align_window_start(chosen, observation, self.num_bands)
        return chosen

    def observe(self, info: dict) -> None:
        """The raw outcome of the step just taken (hits and scans) feeds the shaping terms; see ml/agents/shaping.py."""
        self._shaping.observe(info)

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
        reward = self._shaping.shape(reward, observation, action, self.num_bands)
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
        hp: dict = {
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
        if self.align_window:
            hp["align_window"] = True
        if self.bin_edges:
            hp["bin_edges"] = {k: list(v) for k, v in sorted(self.bin_edges.items())}
        if self.neighbor_features:
            hp["neighbor_features"] = list(self.neighbor_features)
        if self.neighbor_bin_edges:
            hp["neighbor_bin_edges"] = {k: list(v) for k, v in sorted(self.neighbor_bin_edges.items())}
        if self._shaping.eff_beta:
            hp["eff_beta"] = self._shaping.eff_beta
        if self._shaping.cov_beta:
            hp["cov_beta"] = self._shaping.cov_beta
        return hp

    def describe(self) -> dict:
        out: dict = {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "hyperparams": self.hyperparams(),
            "updates": int(self.updates),
            "epsilon": float(self.epsilon),
            "table_size": len(self.q_table),
            "table_capacity": int(np.prod(self._key_bin_counts())),
        }
        if self.align_window:
            out["align_window"] = True
        return out
