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

import gymnasium as gym

from ml.agents.base import Agent, align_window_start

SUPPORTED = ("dqn", "ppo")


class RewardScaleWrapper(gym.RewardWrapper):
    """Multiply every reward by a fixed scale (training-time knob)."""

    def __init__(self, env: gym.Env, reward_scale: float = 1.0) -> None:
        super().__init__(env)
        self.reward_scale = float(reward_scale)

    def reward(self, reward: float) -> float:
        return float(reward) * self.reward_scale


def _patch_torch_load_for_zip_members() -> None:
    """Work around a torch/SB3 incompatibility on this environment.

    SB3's zip loader hands ``torch.load()`` a ``zipfile.ZipExtFile`` (a member stream of the
    outer .zip), and torch's C++ ``PyTorchFileReader`` fails to read it -- "PytorchStreamReader
    failed reading file .data/serialization_id" -- even for a checkpoint saved seconds earlier
    by this same torch build; verified with a vanilla SB3 save/load round trip, so it is not
    specific to this project's checkpoints. The identical bytes load fine once fully buffered,
    so this makes torch.load do that itself whenever it's handed a zip member stream.
    """
    import torch

    if getattr(torch.load, "_zip_member_patch", False):
        return
    original_load = torch.load

    def patched_load(f, *args, **kwargs):
        import io
        import zipfile

        if isinstance(f, zipfile.ZipExtFile):
            f = io.BytesIO(f.read())
        return original_load(f, *args, **kwargs)

    patched_load._zip_member_patch = True
    torch.load = patched_load


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
        policy_hidden: int = 64,
        reward_scale: float = 1.0,
        align_window: bool = False,
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
        self.policy_hidden = int(policy_hidden)
        self.reward_scale = float(reward_scale)
        self.align_window = bool(align_window)
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
        train_env = env
        if float(self.reward_scale) != 1.0:
            train_env = RewardScaleWrapper(env, reward_scale=self.reward_scale)
        if self.sb3_policy == "equivariant":
            from ml.agents.equivariant_policy import (  # noqa: PLC0415 - heavy SB3/torch import, only for V2
                EquivariantDQNPolicy,
                EquivariantPPOPolicy,
            )

            policy_arg = EquivariantDQNPolicy if self.policy_type == "dqn" else EquivariantPPOPolicy
            kwargs["policy_kwargs"] = {
                "num_bands": self.num_bands,
                "hidden": self.policy_hidden,
            }
        else:
            kwargs.setdefault("policy_kwargs", {"net_arch": self.net_arch})
            policy_arg = self.sb3_policy
        if seed is not None:
            kwargs["seed"] = int(seed)

        self.model = cls(policy_arg, train_env, device=self.device, verbose=0, **kwargs)
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
        chosen = int(np.asarray(action).reshape(-1)[0]) % self.num_bands
        if self.align_window:
            return align_window_start(chosen, observation, self.num_bands)
        return chosen

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
        sidecar: dict[str, Any] = {
            "algorithm": self.policy_type,
            "num_bands": self.num_bands,
            "sb3_policy": self.sb3_policy,
            "net_arch": self.net_arch,
            "total_timesteps": self.total_timesteps,
            "policy_hidden": self.policy_hidden,
            "reward_scale": self.reward_scale,
        }
        if self.align_window:
            sidecar["align_window"] = True
        path.with_suffix(".meta.json").write_text(
            json.dumps(sidecar, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "DeepRLAgent":
        from stable_baselines3 import DQN, PPO

        _patch_torch_load_for_zip_members()
        path = Path(path)
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        algorithm = meta.get("algorithm", kwargs.pop("algorithm", "dqn"))

        agent = cls(
            num_bands=int(meta.get("num_bands", kwargs.pop("num_bands", 16))),
            algorithm=algorithm,
            policy=meta.get("sb3_policy", "MlpPolicy"),
            net_arch=meta.get("net_arch"),
            policy_hidden=int(meta.get("policy_hidden", kwargs.pop("policy_hidden", 64))),
            reward_scale=float(meta.get("reward_scale", kwargs.pop("reward_scale", 1.0))),
            align_window=bool(meta.get("align_window", kwargs.pop("align_window", False))),
            **kwargs,
        )
        sb3_cls = DQN if algorithm == "dqn" else PPO
        agent.model = sb3_cls.load(str(path.with_suffix("")), device=agent.device)
        return agent

    def hyperparams(self) -> dict:
        hp: dict[str, Any] = {
            "policy": self.sb3_policy,
            "net_arch": self.net_arch,
            "total_timesteps": self.total_timesteps,
            "device": self.device,
            **self.sb3_kwargs,
        }
        if self.sb3_policy == "equivariant":
            hp["policy_hidden"] = self.policy_hidden
        if float(self.reward_scale) != 1.0:
            hp["reward_scale"] = self.reward_scale
        if self.align_window:
            hp["align_window"] = True
        return hp

    def describe(self) -> dict:
        return {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "hyperparams": self.hyperparams(),
            "trained": self.model is not None,
        }
