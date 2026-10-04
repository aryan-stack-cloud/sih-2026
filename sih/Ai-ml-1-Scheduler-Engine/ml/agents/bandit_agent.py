"""Contextual multi-armed bandit -- the MVP scheduler (PRD Section 10.1, Ai-ml-1 Level 3).

The PRD picks this over Q-Learning and DQN for the MVP because it trains in minutes on CPU and
its estimates stay interpretable (Section 26). Both properties survive here.

MODEL. One arm per band. The value of tuning to band ``a`` in state ``s`` is

    q(s, a) = w . phi_a(s) + b_a

``phi_a(s)`` is that band's seven ML-001 features plus a bias, sliced straight out of the
observation vector. ``w`` is *shared across arms* and ``b_a`` is per-arm.

That split is the whole design. Shared ``w`` learns the transferable rule -- "a band whose
detection-rate EWMA is high, or that is overdue, or whose periodicity phase says it is about to
wake up, is worth visiting" -- from every arm's experience at once, so it converges in a handful
of episodes instead of needing each of 32 bands to be explored independently. Per-arm ``b_a``
then captures what is idiosyncratic about each band, and is exactly the "per-band value
estimate" Level 3 asks for: printable, plottable, and directly checkable against which bands
actually held emitters.

A bandit predicts *immediate* reward and does not bootstrap a future value. That is the honest
formulation of the MVP: it is the Q-Learning and DQN agents' job to reason about consequences
over time, and keeping that distinction sharp is what makes the ladder in Section 10.1 mean
something.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from ml.agents.base import Agent, align_window_start
from ml.agents.shaping import RewardShaping
from ml.algorithms.exploration import EpsilonSchedule, epsilon_greedy
from ml.environments.state import NUM_BAND_FEATURES

# phi_a is the band's features plus a bias term.
FEATURE_DIM = NUM_BAND_FEATURES + 1


class BanditAgent(Agent):
    """Linear contextual bandit with shared feature weights and per-band value estimates."""

    policy_type = "bandit"

    def __init__(
        self,
        num_bands: int,
        learning_rate: float = 0.05,
        bias_learning_rate: float = 0.05,
        reward_scale: float = 10.0,
        optimistic_init: float = 0.5,
        epsilon: EpsilonSchedule | None = None,
        rng: np.random.Generator | None = None,
        align_window: bool = False,
        poly_degree: int = 1,
        poly_features: int = 5,
        neighbor_features: Sequence[int] = (),
        poly_neighbor: bool = False,
        eff_beta: float = 0.0,
        cov_beta: float = 0.0,
    ) -> None:
        super().__init__(num_bands, rng)
        if poly_degree not in (1, 2):
            raise ValueError(f"poly_degree must be 1 or 2, got {poly_degree!r}")
        if poly_features not in (1, 2, 3, 4, 5, 6, 7):
            raise ValueError(f"poly_features must be 1..7, got {poly_features!r}")
        try:
            neighbor_raw = tuple(neighbor_features) if neighbor_features is not None else ()
        except TypeError:
            raise ValueError(
                f"neighbor_features must be a sequence of 0..6, got {neighbor_features!r}"
            ) from None
        neighbor: list[int] = []
        for v in neighbor_raw:
            if isinstance(v, bool) or int(v) != v or not 0 <= int(v) <= NUM_BAND_FEATURES - 1:
                raise ValueError(
                    f"neighbor_features entries must be in 0..6, got {neighbor_features!r}"
                )
            neighbor.append(int(v))
        if float(eff_beta) < 0:
            raise ValueError(f"eff_beta must be >= 0, got {eff_beta!r}")
        if float(cov_beta) < 0:
            raise ValueError(f"cov_beta must be >= 0, got {cov_beta!r}")
        self.learning_rate = float(learning_rate)
        self.bias_learning_rate = float(bias_learning_rate)
        self.reward_scale = float(reward_scale)
        self.optimistic_init = float(optimistic_init)
        self.epsilon_schedule = epsilon or EpsilonSchedule()
        self.align_window = bool(align_window)
        self.poly_degree = int(poly_degree)
        self.poly_features = int(poly_features)
        self.neighbor_features = tuple(neighbor)
        self.poly_neighbor = bool(poly_neighbor)
        self.eff_beta = float(eff_beta)
        self.cov_beta = float(cov_beta)
        self.shaping = RewardShaping(self.eff_beta, self.cov_beta)

        self.weights = np.zeros(self._feature_dim(), dtype=np.float64)
        # Optimistic start: every band looks good until visited, so early episodes sweep the
        # spectrum instead of camping on whichever band happened to pay out first.
        self.band_bias = np.full(num_bands, self.optimistic_init, dtype=np.float64)
        self.visit_counts = np.zeros(num_bands, dtype=np.int64)
        self.epsilon = self.epsilon_schedule.value(0)
        self.updates = 0

    # -- features -------------------------------------------------------------------------

    def _feature_dim(self) -> int:
        """Length of ``phi``: today's 8, plus neighbour columns, plus pairwise products."""
        dim = NUM_BAND_FEATURES + 1 + len(self.neighbor_features)
        if self.poly_degree == 2:
            m = self.poly_features
            if self.poly_neighbor and self.neighbor_features:
                m += len(self.neighbor_features)
            dim += m * (m + 1) // 2
        return dim

    def _band_features(self, observation: np.ndarray) -> np.ndarray:
        """Slice the observation into ``(num_bands, dim)``.

        Layout is fixed by ml/environments/state.py: the first 7N entries are band-major
        per-band features. Column 1-8 are today's features (the band's seven plus a bias
        column, which lets ``w`` learn a global offset); after that come the next band's raw
        features at ``neighbor_features``, then -- only at ``poly_degree == 2`` -- the
        pairwise products of the first ``poly_features`` band features (plus the neighbour
        values when ``poly_neighbor`` is set), which let the linear rule express "detected
        recently AND not scanned for long" instead of scoring each feature in isolation.
        """
        n = self.num_bands
        bands = np.asarray(
            observation[: NUM_BAND_FEATURES * n], dtype=np.float64
        ).reshape(n, NUM_BAND_FEATURES)
        parts: list[np.ndarray] = [bands, np.ones((n, 1), dtype=np.float64)]
        neigh: np.ndarray | None = None
        if self.neighbor_features:
            # The K = 2 window starting at a also covers a + 1, so its features belong in
            # the decision. np.roll(..., -1) puts band (a+1) % N at row a.
            neigh = np.stack(
                [np.roll(bands[:, int(idx)], -1, axis=0) for idx in self.neighbor_features],
                axis=1,
            )
            parts.append(neigh)
        if self.poly_degree == 2:
            src = bands[:, : self.poly_features]
            if self.poly_neighbor and neigh is not None:
                src = np.hstack([src, neigh])
            m = src.shape[1]
            parts.append(
                np.stack(
                    [src[:, i] * src[:, j] for i in range(m) for j in range(i, m)],
                    axis=1,
                )
            )
        return np.hstack(parts)

    def q_values(self, observation: np.ndarray) -> np.ndarray:
        return self._band_features(observation) @ self.weights + self.band_bias

    # -- Agent API ------------------------------------------------------------------------

    def start_episode(self, episode: int = 0) -> None:
        """New episode: keep the learned rule, forget which band was which.

        The shared weights ``w`` are the transferable knowledge and persist across episodes. The
        per-band biases must NOT: emitters are placed on different bands every seed, so "band 7
        pays well" is a fact about one simulation, not about the world. Carrying biases forward
        makes the agent camp on bands that were busy during training and are silent now -- it
        looks like a trained policy and behaves worse than round-robin.

        Resetting to ``optimistic_init`` also gives each episode a clean optimism-driven sweep,
        which is how the agent re-discovers where the emitters are this time. In deployment this
        corresponds to a fresh ``simulation_id``; the Backend calls ``/internal/learn`` every
        step, so the per-band estimates rebuild online within the run.
        """
        self.epsilon = self.epsilon_schedule.value(episode)
        self.band_bias = np.full(self.num_bands, self.optimistic_init, dtype=np.float64)
        self.visit_counts = np.zeros(self.num_bands, dtype=np.int64)

    def select_action(self, observation: np.ndarray, explore: bool = True) -> int:
        chosen = epsilon_greedy(self.q_values(observation), self.epsilon, self.rng, explore)
        if self.align_window:
            return align_window_start(chosen, observation, self.num_bands)
        return chosen

    def learn(
        self,
        observation: np.ndarray,
        action: int,
        reward: float,
        next_observation: np.ndarray,
        done: bool = False,
    ) -> None:
        """Online least-squares update on the chosen arm only.

        Bandit semantics: we observed the payoff of the arm we pulled and know nothing new about
        the others, so only ``band_bias[action]`` moves. The shared ``w`` still moves on every
        step, which is where the cross-band generalisation comes from.

        The target adds the opt-in shaping terms (efficiency/coverage, in the Backend's raw
        reward units, so they are divided by ``reward_scale`` like the reward itself). The
        runner calls ``observe`` before ``learn``, which is where the shaping terms read the
        step's outcome from; with both weights at 0 the reward is unchanged.
        """
        phi = self._band_features(observation)[action]
        shaped = self.shaping.shape(reward, observation, action, self.num_bands)
        target = shaped / self.reward_scale
        error = target - float(phi @ self.weights + self.band_bias[action])

        self.weights += self.learning_rate * error * phi
        self.band_bias[action] += self.bias_learning_rate * error
        self.visit_counts[action] += 1
        self.updates += 1

    def observe(self, info: dict) -> None:
        """Hand the step's raw outcome to the shaping terms. No-op at default weights."""
        self.shaping.observe(info)
        return None

    # -- interpretability -----------------------------------------------------------------

    def feature_weights(self) -> dict[str, float]:
        """The learned rule, in words. Useful for the demo and for sanity-checking training."""
        from ml.environments.state import BAND_FEATURES

        names = [*BAND_FEATURES, "bias"]
        names.extend(f"next_{BAND_FEATURES[int(idx)]}" for idx in self.neighbor_features)
        if self.poly_degree == 2:
            src_names = list(BAND_FEATURES[: self.poly_features])
            if self.poly_neighbor and self.neighbor_features:
                src_names.extend(
                    f"next_{BAND_FEATURES[int(idx)]}" for idx in self.neighbor_features
                )
            names.extend(
                f"{a}*{b}" for i, a in enumerate(src_names) for b in src_names[i:]
            )
        return {name: float(w) for name, w in zip(names, self.weights)}

    def band_values(self) -> np.ndarray:
        return self.band_bias.copy()

    # -- persistence ----------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            weights=self.weights,
            band_bias=self.band_bias,
            visit_counts=self.visit_counts,
            num_bands=self.num_bands,
            hyperparams=json.dumps(self.hyperparams()),
        )

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "BanditAgent":
        data = np.load(Path(path), allow_pickle=False)
        hp = json.loads(str(data["hyperparams"]))
        eps = EpsilonSchedule(**hp.pop("epsilon"))
        agent = cls(num_bands=int(data["num_bands"]), epsilon=eps, **hp, **kwargs)
        agent.weights = data["weights"]
        agent.band_bias = data["band_bias"]
        agent.visit_counts = data["visit_counts"]
        if agent.weights.shape[0] != agent._feature_dim():
            raise ValueError(
                f"checkpoint weight length {agent.weights.shape[0]} does not match the saved "
                f"options (poly_degree={agent.poly_degree}, "
                f"poly_features={agent.poly_features}, "
                f"neighbor_features={list(agent.neighbor_features)}, "
                f"poly_neighbor={agent.poly_neighbor}): "
                f"expected {agent._feature_dim()}"
            )
        # A loaded model is for inference: stop exploring unless a caller re-enables it.
        agent.epsilon = eps.end
        return agent

    def hyperparams(self) -> dict:
        hp: dict = {
            "learning_rate": self.learning_rate,
            "bias_learning_rate": self.bias_learning_rate,
            "reward_scale": self.reward_scale,
            "optimistic_init": self.optimistic_init,
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
        # Each option is reported only when it differs from its default, so the registry
        # record of a default model -- and every existing checkpoint -- is unchanged.
        if self.poly_degree != 1:
            hp["poly_degree"] = self.poly_degree
        if self.poly_features != 5:
            hp["poly_features"] = self.poly_features
        if self.neighbor_features:
            hp["neighbor_features"] = list(self.neighbor_features)
        if self.poly_neighbor:
            hp["poly_neighbor"] = True
        if self.eff_beta != 0.0:
            hp["eff_beta"] = self.eff_beta
        if self.cov_beta != 0.0:
            hp["cov_beta"] = self.cov_beta
        return hp

    def describe(self) -> dict:
        out: dict = {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "hyperparams": self.hyperparams(),
            "updates": int(self.updates),
            "epsilon": float(self.epsilon),
            "feature_weights": self.feature_weights(),
            "band_values": self.band_bias.round(4).tolist(),
            "visit_counts": self.visit_counts.tolist(),
        }
        if self.align_window:
            out["align_window"] = True
        return out
