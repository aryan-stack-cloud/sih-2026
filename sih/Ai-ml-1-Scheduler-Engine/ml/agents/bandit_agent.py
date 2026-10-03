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
from pathlib import Path

import numpy as np

from ml.agents.base import Agent
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
    ) -> None:
        super().__init__(num_bands, rng)
        self.learning_rate = float(learning_rate)
        self.bias_learning_rate = float(bias_learning_rate)
        self.reward_scale = float(reward_scale)
        self.optimistic_init = float(optimistic_init)
        self.epsilon_schedule = epsilon or EpsilonSchedule()

        self.weights = np.zeros(FEATURE_DIM, dtype=np.float64)
        # Optimistic start: every band looks good until visited, so early episodes sweep the
        # spectrum instead of camping on whichever band happened to pay out first.
        self.band_bias = np.full(num_bands, self.optimistic_init, dtype=np.float64)
        self.visit_counts = np.zeros(num_bands, dtype=np.int64)
        self.epsilon = self.epsilon_schedule.value(0)
        self.updates = 0

    # -- features -------------------------------------------------------------------------

    def _band_features(self, observation: np.ndarray) -> np.ndarray:
        """Slice the observation into ``(num_bands, FEATURE_DIM)``.

        Layout is fixed by ml/environments/state.py: the first 7N entries are band-major
        per-band features. The trailing bias column lets ``w`` learn a global offset.
        """
        n = self.num_bands
        bands = np.asarray(
            observation[: NUM_BAND_FEATURES * n], dtype=np.float64
        ).reshape(n, NUM_BAND_FEATURES)
        return np.hstack([bands, np.ones((n, 1), dtype=np.float64)])

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
        return epsilon_greedy(self.q_values(observation), self.epsilon, self.rng, explore)

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
        """
        phi = self._band_features(observation)[action]
        target = float(reward) / self.reward_scale
        error = target - float(phi @ self.weights + self.band_bias[action])

        self.weights += self.learning_rate * error * phi
        self.band_bias[action] += self.bias_learning_rate * error
        self.visit_counts[action] += 1
        self.updates += 1

    # -- interpretability -----------------------------------------------------------------

    def feature_weights(self) -> dict[str, float]:
        """The learned rule, in words. Useful for the demo and for sanity-checking training."""
        from ml.environments.state import BAND_FEATURES

        names = [*BAND_FEATURES, "bias"]
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
        # A loaded model is for inference: stop exploring unless a caller re-enables it.
        agent.epsilon = eps.end
        return agent

    def hyperparams(self) -> dict:
        return {
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

    def describe(self) -> dict:
        return {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "hyperparams": self.hyperparams(),
            "updates": int(self.updates),
            "epsilon": float(self.epsilon),
            "feature_weights": self.feature_weights(),
            "band_values": self.band_bias.round(4).tolist(),
            "visit_counts": self.visit_counts.tolist(),
        }
