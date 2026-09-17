"""EWEnvironment -- the Gymnasium environment (Ai-ml-1 README, Level 2).

One episode is one full simulation run of fixed duration T, terminal at t = T (PRD Section 10.4).
Each step follows the PRD Section 8.2 loop exactly:

    spectrum.advance(t)         -> read the pre-computed ground-truth row for t
    scanner.execute(action)     -> Observation, subject to K / dwell / tuning-delay constraints
    detection_engine.evaluate() -> TP / FN / FP / TN events
    reward_fn(...)              -> Equation 10.1
    state_builder.update(...)   -> the ML-001 features the agent sees next step
    metrics.record(...)         -> everything ml/evaluation/evaluator.py needs

The observation returned to the agent is ``StateBuilder.to_vector()`` and the identical state is
available as the contract StateVector via ``env.state_vector()``. The ground-truth table is never
part of the observation (PRD Section 8.1) -- it reaches the agent only through the reward.
"""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np

from ml.environments.action_space import ActionSpaceSpec
from ml.environments.emitters import build_emitters
from ml.environments.receiver import (
    DetectionEngine,
    Receiver,
    ReceiverConfig,
    Scanner,
)
from ml.environments.reward import RewardContext, RewardFunction, RewardWeights
from ml.environments.spectrum import GroundTruth, Spectrum
from ml.environments.state import StateBuilder, StateNormalisation
from ml.features.periodicity_provider import (
    LocalPeriodicityProvider,
    NullPeriodicityProvider,
    PeriodicityProvider,
)
from ml.utils.seeding import make_seed_bundle


class EWEnvironment(gym.Env):
    """Bandwidth-constrained scan scheduling over a synthetic RF spectrum."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        num_bands: int = 16,
        duration_steps: int = 2000,
        num_emitters: int = 10,
        emitter_mix: dict[str, float] | None = None,
        receiver_config: ReceiverConfig | None = None,
        reward_weights: RewardWeights | None = None,
        seed: int = 42,
        dwell_options: tuple[int, ...] = (),
        periodicity_provider: PeriodicityProvider | None = None,
        ground_truth: GroundTruth | None = None,
        high_priority_fraction: float = 0.25,
        emitter_params: dict[str, dict] | None = None,
        band_priority_weights: np.ndarray | None = None,
        scenario_id: str | None = None,
    ) -> None:
        super().__init__()

        self.num_bands = num_bands
        self.duration_steps = duration_steps
        self.num_emitters = num_emitters
        self.emitter_mix = emitter_mix or {
            "fixed": 0.2, "periodic": 0.2, "agile": 0.2, "random": 0.2, "intermittent": 0.2
        }
        self.emitter_params = emitter_params or {}
        self.high_priority_fraction = high_priority_fraction
        self.scenario_id = scenario_id

        self.receiver_config = receiver_config or ReceiverConfig()
        self.reward_fn = RewardFunction(reward_weights)
        self.seed_value = seed
        self._fixed_ground_truth = ground_truth

        # Training runs stand in for Ai-ml-2 so the periodicity features carry signal while the
        # agent learns; see ml/features/periodicity_provider.py for why.
        self.periodicity: PeriodicityProvider = (
            periodicity_provider if periodicity_provider is not None else LocalPeriodicityProvider()
        )

        self.spectrum = Spectrum(num_bands, priority_weights=band_priority_weights)
        self.action_spec = ActionSpaceSpec(num_bands=num_bands, dwell_options=dwell_options)
        self.action_space = self.action_spec.to_gym()
        self.observation_space = gym.spaces.Box(
            low=0.0,
            high=1.0,
            shape=(StateBuilder.vector_size(num_bands),),
            dtype=np.float32,
        )

        self.state_builder = StateBuilder(
            num_bands, band_priority_weights=self.spectrum.priority_weights
        )
        self.receiver = Receiver(self.receiver_config, num_bands)

        self.ground_truth: GroundTruth | None = None
        self.t = 0
        self.history: list[dict[str, Any]] = []
        self._detected_runs: set[tuple[int, int]] = set()

    # -- gymnasium API ---------------------------------------------------------------------

    def reset(
        self, *, seed: int | None = None, options: dict | None = None
    ) -> tuple[np.ndarray, dict]:
        if seed is not None:
            self.seed_value = int(seed)
        super().reset(seed=self.seed_value)

        bundle = make_seed_bundle(self.seed_value)
        self._noise_rng = bundle.noise
        self.policy_rng = bundle.policy

        if self._fixed_ground_truth is not None:
            self.ground_truth = self._fixed_ground_truth
            self.duration_steps = min(self.duration_steps, self.ground_truth.duration)
            self.emitters = self.ground_truth.emitters
        else:
            self.emitters = build_emitters(
                self.num_emitters,
                self.num_bands,
                self.emitter_mix,
                bundle.ground_truth,
                high_priority_fraction=self.high_priority_fraction,
                params_by_class=self.emitter_params,
            )
            self.ground_truth = self.spectrum.generate_ground_truth(
                self.emitters, self.duration_steps, bundle.ground_truth
            )

        self.receiver.reset(tuned_start=0)
        self.scanner = Scanner(self.receiver, self._noise_rng)
        self.detection_engine = DetectionEngine(self.receiver_config.threshold)
        self.state_builder.reset()
        self.periodicity.reset(self.num_bands)
        self.t = 0
        self.history = []
        self._detected_runs: set[tuple[int, int]] = set()

        # Seed the receiver block of the state so step 0 sees a coherent receiver.
        self.state_builder.update([], [], self.receiver.state, self.receiver_config.bandwidth_k)
        return self.state_builder.to_vector(), {"scenario_id": self.scenario_id}

    def step(self, action) -> tuple[np.ndarray, float, bool, bool, dict]:
        if self.ground_truth is None:
            raise RuntimeError("call reset() before step()")

        t = self.t
        next_band, dwell = self.action_spec.decode(action)
        if dwell is not None:
            # V2 dwell control: the agent trades integration time against revisit rate.
            self.receiver.config.dwell_ms = min(dwell, self.receiver.config.step_ms)

        gt = self.ground_truth
        occupancy_row = gt.occupancy[t]
        # Snapshot the ages BEFORE the state update; C(t) asks how recently we were last here.
        time_since_last_scan = self.state_builder.time_since_last_scan.copy()

        observation = self.scanner.execute(t, next_band, occupancy_row)
        outcome = self.detection_engine.evaluate(
            observation, occupancy_row, gt.owner[t], gt.priority[t], gt.activation_starts[t]
        )

        # Which of this step's detections intercepted an activation run we had not yet caught.
        # L(t) is charged on these only -- see ml/environments/reward.py.
        new_run_latencies: dict[int, int] = {}
        for band, latency in outcome.detection_latency.items():
            key = (int(band), int(gt.activation_starts[t, band]))
            if key not in self._detected_runs:
                self._detected_runs.add(key)
                new_run_latencies[band] = latency

        context = RewardContext(
            time_since_last_scan=time_since_last_scan,
            high_priority_active=gt.high_priority_mask(t),
            scanned_bands=list(observation.tuned_bands) if observation.valid else [],
            new_run_latencies=new_run_latencies,
            latency_horizon=max(2, self.num_bands),
        )
        reward, terms = self.reward_fn.compute(outcome, context)

        for b in outcome.detected_bands:
            self.periodicity.observe_detection(b, t)

        self.state_builder.update(
            context.scanned_bands,
            outcome.detected_bands,
            self.receiver.state,
            self.receiver_config.bandwidth_k,
        )
        phase, confidence = self.periodicity.features(t)
        self.state_builder.set_periodicity(phase, confidence)

        self.history.append(
            {
                "t": t,
                "action": int(next_band),
                "scanned_bands": list(context.scanned_bands),
                "valid": bool(observation.valid),
                "retuned": bool(observation.retuned),
                "outcomes": dict(outcome.outcomes),
                "unscanned_misses": list(outcome.unscanned_misses),
                "detected_bands": list(outcome.detected_bands),
                "detected_emitters": set(outcome.detected_emitters),
                "false_alarm_bands": list(outcome.false_alarm_bands),
                "detection_latency": dict(outcome.detection_latency),
                "reward": float(reward),
                "terms": terms,
            }
        )

        self.t += 1
        truncated = self.t >= self.duration_steps
        info = {
            "terms": terms,
            "scanned_bands": context.scanned_bands,
            "detected_bands": outcome.detected_bands,
            "valid_observation": observation.valid,
        }
        return self.state_builder.to_vector(), float(reward), False, truncated, info

    # -- contract + introspection ----------------------------------------------------------

    def state_vector(self) -> dict:
        """The current state as the API_CONTRACT.md Section 4 StateVector."""
        return self.state_builder.to_contract()

    def action_to_contract(self, action) -> dict:
        return self.action_spec.to_contract(action)

    @property
    def reward_weights(self) -> dict[str, float]:
        return self.reward_fn.weights.as_dict()


def make_env(config: dict, seed: int | None = None, **overrides) -> EWEnvironment:
    """Build an EWEnvironment from a scenario config dict (ml/experiments/scenario_*.yaml)."""
    receiver_cfg = ReceiverConfig(**config.get("receiver", {}))
    weights = RewardWeights.from_config(config.get("reward_weights"))
    kwargs: dict[str, Any] = {
        "num_bands": config["bands"],
        "duration_steps": config["duration_steps"],
        "num_emitters": config["emitters"],
        "emitter_mix": config["emitter_mix"],
        "receiver_config": receiver_cfg,
        "reward_weights": weights,
        "seed": seed if seed is not None else config.get("seed", 42),
        "scenario_id": config.get("scenario_id"),
        "high_priority_fraction": config.get("high_priority_fraction", 0.25),
        "emitter_params": config.get("emitter_params"),
    }
    kwargs.update(overrides)
    return EWEnvironment(**kwargs)


def null_periodicity_env(config: dict, seed: int | None = None, **overrides) -> EWEnvironment:
    """Same scenario with the periodicity features pinned to zero.

    Used for the PRD Definition-of-Done item 8 A/B: Scenario B with and without periodicity
    features feeding the RL state.
    """
    return make_env(
        config, seed=seed, periodicity_provider=NullPeriodicityProvider(), **overrides
    )
