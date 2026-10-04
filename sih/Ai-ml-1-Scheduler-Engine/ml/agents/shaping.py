"""Agent-side reward shaping for the learned policies (opt-in; both weights default to 0, which changes nothing).

The reward the Backend posts to ``/internal/learn`` (Equation 10.1) pays ``D(t) = 1`` for ANY detection in the receiver window,
so a window with two active bands pays the same as one with a single active band, and nothing pays for looking at a band that
has not been looked at for a long time except the first detection of a run. Two small, transparent terms move a learner along
the listening-efficiency / coverage trade-off without touching the Backend's reward:

    r' = r + eff_beta * (detected bands in the window) / (scanned bands in the window)     # listening efficiency
           + cov_beta * mean over the scanned bands of min(age, 32) / 32                   # coverage (staleness)

``age`` is the band's ``time_since_last_scan`` BEFORE the step (the same normaliser as ml.environments.state, 32 steps).
Tabular agents add the terms in ``learn()`` (the raw outcome arrives through ``Agent.observe`` first, exactly as the runner
and ``/internal/learn`` do it); DQN/PPO learn offline, so the same terms are applied by an environment wrapper at training
time (ml/agents/dqn_agent.py).
"""

from __future__ import annotations

import numpy as np

from ml.environments.state import NUM_BAND_FEATURES

AGE_FEATURE = 0          # index of time_since_last_scan in BAND_FEATURES
AGE_NORMALISER = 32.0    # StateNormalisation.time_since_last_scan


def hit_share(info: dict) -> float:
    """Detected bands over scanned bands for one step; 0 when nothing was scanned."""
    scanned = info.get("scanned_bands") or []
    if not scanned:
        return 0.0
    return len(info.get("detected_bands") or []) / len(scanned)


def staleness_from_ages(ages, scanned_bands) -> float:
    """Mean of min(age, 32) / 32 over the scanned bands (``ages`` in steps); 0 when nothing was scanned."""
    if not scanned_bands:
        return 0.0
    return float(sum(min(float(ages[int(b)]), AGE_NORMALISER) / AGE_NORMALISER for b in scanned_bands) / len(scanned_bands))


def staleness_from_observation(observation, action: int, num_bands: int) -> float:
    """Staleness of the executed window read from the (normalised) pre-step observation.

    The window size K is the number of ones in the tuned-bands block; the window is ``action .. action + K - 1`` (wrapping).
    """
    n = int(num_bands)
    obs = np.asarray(observation, dtype=np.float64)
    k = max(1, int(round(float(obs[NUM_BAND_FEATURES * n:(NUM_BAND_FEATURES + 1) * n].sum()))))
    bands = [(int(action) + i) % n for i in range(k)]
    return float(sum(obs[b * NUM_BAND_FEATURES + AGE_FEATURE] for b in bands) / k)


class RewardShaping:
    """Holds the two weights and the last step's hit share; ``shape`` returns the shaped reward."""

    def __init__(self, eff_beta: float = 0.0, cov_beta: float = 0.0) -> None:
        self.eff_beta = float(eff_beta)
        self.cov_beta = float(cov_beta)
        self._hits = 0.0

    @property
    def active(self) -> bool:
        return self.eff_beta != 0.0 or self.cov_beta != 0.0

    def observe(self, info: dict) -> None:
        self._hits = hit_share(info)

    def shape(self, reward: float, observation, action: int, num_bands: int) -> float:
        shaped = float(reward)
        if self.eff_beta:
            shaped += self.eff_beta * self._hits
        if self.cov_beta:
            shaped += self.cov_beta * staleness_from_observation(observation, action, num_bands)
        return shaped
