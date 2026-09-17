"""DQN / PPO via Stable-Baselines3 -- V2 stretch (PRD Section 7, Ai-ml-1 Level 9).

GATE. The Ai-ml-1 README and PRD Section 24 both require the contextual bandit to demonstrably
beat the open-loop baseline on Scenario A/B before this level is built, and name "scope creep
toward Deep RL too early" as an explicit risk. This module exists, and is deliberately not the
default in any config or script.

The point of the Gymnasium environment interface (ADR: "Gymnasium environment interface ...
interoperable with Stable-Baselines3 for V2 escalation") is that nothing here re-implements the
problem: SB3 trains directly against the same ``EWEnvironment`` the bandit and Q-Learner use,
against the same observation vector and the same reward. So a DQN result is comparable to a
bandit result by construction rather than by hoping two implementations agree.

One structural difference from the tabular agents, and it matters for the contract: SB3 learns
from its own rollouts inside ``model.learn()``, so ``/internal/learn`` cannot feed it transitions
one at a time. ``Agent.learn`` is therefore a no-op here and the Backend's per-step calls are
acknowledged without changing the policy -- an SB3 model is trained offline via
``/internal/train`` and then served read-only. That is why ``/internal/decide`` needs no Backend
changes to switch policy (the Level 9 Definition of Done).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ml.agents.base import Agent

SUPPORTED = ("dqn", "ppo")


class DeepRLAgent(Agent):
    """Wraps an SB3 DQN or PPO model behind the shared Agent interface."""

    def __init__(
        self,
        num_bands: int,
        algorithm: str = "dqn",
        policy: str = "MlpPolicy",
        net_arch: list[int] | None = None,
        device: str = "auto",
        rng: np.random.Generator | None = None,
        **sb3_kwargs: Any,
    ) -> None:
        super().__init__(num_bands, rng)
        algorithm = str(algorithm).lower()
        if algorithm not in SUPPORTED:
            raise ValueError(f"algorithm must be one of {SUPPORTED}, got {algorithm!r}")
        self.policy_type = algorithm
        self.sb3_policy = policy
        self.net_arch = list(net_arch) if net_arch else [128, 128]
        self.device = device
        # total_timesteps belongs to the training call, not the model constructor.
        self.total_timesteps = int(sb3_kwargs.pop("total_timesteps", 50_000))
        self.sb3_kwargs = sb3_kwargs
        self.model = None

    # -- training -------------------------------------------------------------------------

    def fit(self, env, total_timesteps: int | None = None, seed: int | None = None, callback=None):
        """Train against an EWEnvironment. This is the only place the policy changes."""
        from stable_baselines3 import DQN, PPO

        cls = DQN if self.policy_type == "dqn" else PPO
        kwargs = dict(self.sb3_kwargs)
        kwargs.setdefault("policy_kwargs", {"net_arch": self.net_arch})
        if seed is not None:
            kwargs["seed"] = int(seed)

        self.model = cls(self.sb3_policy, env, device=self.device, verbose=0, **kwargs)
        self.model.learn(
            total_timesteps=int(total_timesteps or self.total_timesteps),
            callback=callback,
            progress_bar=False,
        )
        return self

    # -- Agent API ------------------------------------------------------------------------

    def select_action(self, observation: np.ndarray, explore: bool = True) -> int:
        if self.model is None:
            raise RuntimeError(
                f"{self.policy_type} agent has no trained model; call fit() or load() first"
            )
        action, _ = self.model.predict(np.asarray(observation), deterministic=not explore)
        return int(np.asarray(action).reshape(-1)[0]) % self.num_bands

    def learn(self, observation, action, reward, next_observation, done: bool = False) -> None:
        """No-op. SB3 owns its own replay/rollout buffer; see the module docstring."""
        return None

    # -- persistence ----------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("nothing to save: model has not been trained")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # SB3 appends .zip itself; keep the sidecar next to it under the same stem.
        self.model.save(str(path.with_suffix("")))
        path.with_suffix(".meta.json").write_text(
            json.dumps(
                {
                    "algorithm": self.policy_type,
                    "num_bands": self.num_bands,
                    "sb3_policy": self.sb3_policy,
                    "net_arch": self.net_arch,
                    "total_timesteps": self.total_timesteps,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "DeepRLAgent":
        from stable_baselines3 import DQN, PPO

        path = Path(path)
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        algorithm = meta.get("algorithm", kwargs.pop("algorithm", "dqn"))

        agent = cls(
            num_bands=int(meta.get("num_bands", kwargs.pop("num_bands", 16))),
            algorithm=algorithm,
            policy=meta.get("sb3_policy", "MlpPolicy"),
            net_arch=meta.get("net_arch"),
            **kwargs,
        )
        sb3_cls = DQN if algorithm == "dqn" else PPO
        agent.model = sb3_cls.load(str(path.with_suffix("")), device=agent.device)
        return agent

    def hyperparams(self) -> dict:
        return {
            "policy": self.sb3_policy,
            "net_arch": self.net_arch,
            "total_timesteps": self.total_timesteps,
            "device": self.device,
            **self.sb3_kwargs,
        }

    def describe(self) -> dict:
        return {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "hyperparams": self.hyperparams(),
            "trained": self.model is not None,
        }
