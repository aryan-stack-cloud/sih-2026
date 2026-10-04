"""Permutation-equivariant policies for DQN and PPO.

The flat observation is ``8N+2`` numbers: seven features per band (band-major),
a tuned-bands one-hot, then two receiver scalars. A plain MLP has to learn
"a band with high detection EWMA is worth tuning to" separately for every band
index; sharing one weight vector across bands (like the bandit) learns it once.

For every band ``a`` the shared input is::

    z_a = [f_a (7), f_{a+1} (7), tuned_a (1), tuned_{a+1} (1), recv (2), g (7)]

with ``f_{a+1}`` the next band wrapping at the top of the spectrum, ``g`` the
mean of the seven features over all bands and ``recv`` the two receiver
scalars. A shared ``Linear(25,H) -> ReLU -> Linear(H,H) -> ReLU`` gives
embeddings ``h_a`` and ``Linear(H,1)`` gives the score ``s_a``. Shifting the
three observation blocks by ``s`` bands shifts the scores by ``s``.
"""

from __future__ import annotations

from functools import partial
from typing import Any

import torch as th
from torch import nn


class BandScorer(nn.Module):
    """Shared per-band scorer: flat obs ``(B, 8N+2)`` -> ``(scores (B,N), pooled (B,2H))``."""

    def __init__(self, num_bands: int, hidden: int = 64) -> None:
        super().__init__()
        self.num_bands = int(num_bands)
        self.hidden = int(hidden)
        self.trunk = nn.Sequential(
            nn.Linear(25, self.hidden),
            nn.ReLU(),
            nn.Linear(self.hidden, self.hidden),
            nn.ReLU(),
        )
        self.score = nn.Linear(self.hidden, 1)

    def forward(self, obs: th.Tensor) -> tuple[th.Tensor, th.Tensor]:
        b = obs.shape[0]
        n = self.num_bands
        feats = obs[:, :7 * n].reshape(b, n, 7)
        tuned = obs[:, 7 * n:8 * n]
        recv = obs[:, 8 * n:8 * n + 2]
        g = feats.mean(dim=1)
        f_next = th.roll(feats, shifts=-1, dims=1)
        tuned_next = th.roll(tuned, shifts=-1, dims=1)
        z = th.cat(
            [
                feats,
                f_next,
                tuned.unsqueeze(-1),
                tuned_next.unsqueeze(-1),
                recv.unsqueeze(1).expand(b, n, 2),
                g.unsqueeze(1).expand(b, n, 7),
            ],
            dim=-1,
        )
        h = self.trunk(z)
        s = self.score(h).squeeze(-1)
        pooled = th.cat([h.mean(dim=1), h.max(dim=1).values], dim=-1)
        return s, pooled


class _QScorerHead(nn.Module):
    """Adapts a BandScorer to the QNetwork ``q_net`` interface (scores only)."""

    def __init__(self, scorer: BandScorer) -> None:
        super().__init__()
        self.scorer = scorer

    def forward(self, x: th.Tensor) -> th.Tensor:
        scores, _ = self.scorer(x)
        return scores


# -- DQN ------------------------------------------------------------------------------------------------

try:
    from stable_baselines3.dqn.policies import DQNPolicy, QNetwork
except Exception:  # pragma: no cover - SB3 is a hard dependency here, kept importable without it
    DQNPolicy = object  # type: ignore[assignment,misc]
    QNetwork = object  # type: ignore[assignment,misc]


class EquivariantQNetwork(QNetwork):  # type: ignore[misc]
    """Q-network whose head is the shared band scorer."""

    def __init__(
        self,
        observation_space,
        action_space,
        features_extractor,
        features_dim: int,
        num_bands: int,
        hidden: int = 64,
        net_arch=None,
        activation_fn: type[nn.Module] = nn.ReLU,
        normalize_images: bool = True,
    ) -> None:
        self.num_bands = int(num_bands)
        self.hidden = int(hidden)
        super().__init__(
            observation_space,
            action_space,
            features_extractor,
            features_dim,
            net_arch=net_arch,
            activation_fn=activation_fn,
            normalize_images=normalize_images,
        )
        self.scorer = BandScorer(self.num_bands, self.hidden)
        self.q_net = _QScorerHead(self.scorer)

    def _get_constructor_parameters(self) -> dict[str, Any]:
        data = super()._get_constructor_parameters()
        data.update({"num_bands": self.num_bands, "hidden": self.hidden})
        return data


class EquivariantDQNPolicy(DQNPolicy):  # type: ignore[misc]
    """DQN policy wiring the equivariant Q-network."""

    def __init__(
        self,
        observation_space,
        action_space,
        lr_schedule,
        num_bands: int,
        hidden: int = 64,
        *args,
        **kwargs,
    ) -> None:
        self.num_bands = int(num_bands)
        self.hidden = int(hidden)
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)

    def make_q_net(self):
        net_args = self._update_features_extractor(self.net_args, features_extractor=None)
        net_args.update({"num_bands": self.num_bands, "hidden": self.hidden})
        return EquivariantQNetwork(**net_args).to(self.device)

    def _get_constructor_parameters(self) -> dict[str, Any]:
        data = super()._get_constructor_parameters()
        data.update({"num_bands": self.num_bands, "hidden": self.hidden})
        return data


# -- PPO ------------------------------------------------------------------------------------------------

try:
    from stable_baselines3.common.policies import ActorCriticPolicy
except Exception:  # pragma: no cover
    ActorCriticPolicy = object  # type: ignore[assignment,misc]


class EquivariantExtractor(nn.Module):
    """MLP-extractor whose actor output already is the action logits.

    ``forward_actor`` returns the per-band scores ``(B, N)`` (``latent_dim_pi = N``)
    and ``forward_critic`` returns the pooled embedding ``(B, 2H)``.
    """

    def __init__(self, feature_dim: int, num_bands: int, hidden: int = 64) -> None:
        super().__init__()
        self.feature_dim = int(feature_dim)
        self.num_bands = int(num_bands)
        self.hidden = int(hidden)
        self.scorer = BandScorer(self.num_bands, self.hidden)
        self.latent_dim_pi = self.num_bands
        self.latent_dim_vf = 2 * self.hidden

    def forward(self, features: th.Tensor) -> tuple[th.Tensor, th.Tensor]:
        return self.forward_actor(features), self.forward_critic(features)

    def forward_actor(self, features: th.Tensor) -> th.Tensor:
        scores, _ = self.scorer(features)
        return scores

    def forward_critic(self, features: th.Tensor) -> th.Tensor:
        _, pooled = self.scorer(features)
        return pooled


class EquivariantPPOPolicy(ActorCriticPolicy):  # type: ignore[misc]
    """Actor-critic policy with the shared band scorer.

    The extractor's actor output already is the logits, so SB3's ``action_net``
    becomes an identity; the value head maps the pooled embedding through
    ``Linear(2H,H) -> ReLU -> Linear(H,1)``.
    """

    def __init__(
        self,
        observation_space,
        action_space,
        lr_schedule,
        num_bands: int,
        hidden: int = 64,
        *args,
        **kwargs,
    ) -> None:
        self.num_bands = int(num_bands)
        self.hidden = int(hidden)
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
        # The shared trunk got SB3's default orthogonal init (gain sqrt(2));
        # shrink the score head so the initial policy is near uniform, the
        # same reason SB3 inits its own action_net with gain 0.01.
        with th.no_grad():
            th.nn.init.orthogonal_(self.mlp_extractor.scorer.score.weight, gain=0.01)
            if self.mlp_extractor.scorer.score.bias is not None:
                self.mlp_extractor.scorer.score.bias.zero_()

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = EquivariantExtractor(
            self.features_dim, self.num_bands, self.hidden
        ).to(self.device)

    def _build(self, lr_schedule) -> None:
        super()._build(lr_schedule)
        # Actor output already is the logits; keep the value head above.
        self.action_net = nn.Identity()
        self.value_net = nn.Sequential(
            nn.Linear(2 * self.hidden, self.hidden),
            nn.ReLU(),
            nn.Linear(self.hidden, 1),
        ).to(self.device)
        if self.ortho_init:
            self.value_net.apply(partial(self.init_weights, gain=1.0))
        # The optimizer was built around the discarded heads; rebuild it so it
        # owns the replacement value head's parameters.
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs
        )

    def _get_constructor_parameters(self) -> dict[str, Any]:
        data = super()._get_constructor_parameters()
        data.update({"num_bands": self.num_bands, "hidden": self.hidden})
        return data
