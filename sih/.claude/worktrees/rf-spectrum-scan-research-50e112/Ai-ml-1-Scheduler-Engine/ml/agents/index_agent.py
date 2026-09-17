"""IndexAgent -- the SCT scheduler as a contract-shaped policy (solution spec Section 9).

Wires the four derived pieces together:

* ``ml/belief/occupancy.py``    what we believe each band is doing right now
* ``ml/scheduling/deadlines.py``  what coverage we owe each band, and when
* ``ml/environments/detection_model.py``  what a dwell of a given length would actually buy
* ``ml/scheduling/index_policy.py``  the index that turns those into one number per band

There is nothing learned in the decision itself. Every term is derived from a mission requirement
or a measured quantity, and every decision decomposes into five named numbers that
``last_breakdown`` hands to the dashboard and the decision log. That is what makes this defensible
in a review in a way a deep network is not, and it is why the DQN and PPO agents stay in the
repository as comparison arms rather than as the answer.

The agent tracks its own ``time_since_last_scan`` through :meth:`observe` instead of reading it
back out of the observation vector. The vector normalises that feature by 32 and clips at 1.0,
which would quietly flatten exactly the staleness range the deadline cares about.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

from ml.agents.base import Agent
from ml.agents.ctmc_floor import CTMCFloorAgent
from ml.belief.kernel_learning import KernelEstimator
from ml.belief.occupancy import OccupancyBelief
from ml.environments.detection_model import DetectionModel, best_dwell
from ml.environments.state import BAND_FEATURES, NUM_BAND_FEATURES
from ml.scheduling.deadlines import TRIGGER_DITHER, RevisitDeadlines
from ml.scheduling.index_policy import (
    IndexInputs,
    IndexWeights,
    apply_deadline_override,
    compute_index,
    select_window,
)

_PRIORITY_FEATURE = BAND_FEATURES.index("band_priority_weight")
_PHASE_FEATURE = BAND_FEATURES.index("periodicity_phase")
_CONFIDENCE_FEATURE = BAND_FEATURES.index("periodicity_confidence")

# Fraction of the revisit deadline that the guaranteed coverage cycle is allowed to consume, when
# the deadline is derived from a scenario rather than from a stated worst-case intercept
# requirement. A deadline equal to the cycle is round-robin with extra steps; this leaves most of
# the receiver time for value seeking while keeping the guarantee. In a real deployment the
# deadline comes from ``revisit_deadline_seconds`` instead, and the feasibility check reports
# whether the receiver is large enough to honour it.
#
# 0.5 is not a guess. scripts/coverage_frontier.py walks this dial across scenarios A, B, C and D,
# and 0.5 is the tightest point at which coverage is still held: run intercept rate and censored
# intercept time stay within about 2% of round-robin on every scenario while detection rises 17 to
# 28% and high-priority detection 12 to 40%. Interception ratio improves everywhere.
#
# The curve is monotone in both directions, so the choice is real. Above 0.5 the deadline is tight
# enough that the hard override fires constantly and drags the schedule back toward a fixed
# rotation, which costs detection *and* coverage. Below 0.4 the policy starts buying detection with
# coverage, which is the direction the contextual bandit takes far too far.
COVERAGE_BUDGET = 0.5

# Confidence at or above which a band counts as characterised. One threshold governs both where
# the randomised floor looks and how much of the receiver's time it gets, so the two halves can
# never disagree about what is already understood.
FLOOR_CONFIDENCE_THRESHOLD = 0.6


class IndexAgent(Agent):
    """Whittle-style index scheduling under hard revisit deadlines."""

    policy_type = "index"

    def __init__(
        self,
        num_bands: int,
        bandwidth_k: int = 1,
        mode: str = "contiguous",
        slot_s: float = 0.010,
        retune_s: float = 0.005,
        deadline_s: float = 0.280,
        trigger_dither: float = TRIGGER_DITHER,
        p_fa: float = 1e-3,
        n_eff: float = 100.0,
        snr_prior: float = 0.3,
        detect_p_d: float | None = None,
        detect_p_fa: float | None = None,
        p01: float = 0.05,
        p10: float = 0.05,
        dwell_options: tuple[int, ...] = (1, 2, 4, 8),
        weights: IndexWeights | None = None,
        learn_kernels: bool = True,
        kernel_refresh_steps: int = 200,
        rho_min: float = 0.10,
        rho_max: float = 1.0,
        floor_mean_dwell_slots: float = 1.0,
        floor_confidence_threshold: float = FLOOR_CONFIDENCE_THRESHOLD,
        rng=None,
    ) -> None:
        super().__init__(num_bands, rng)
        self.bandwidth_k = int(bandwidth_k)
        self.mode = mode
        self.slot_s = float(slot_s)
        self.retune_s = float(retune_s)
        self.snr_prior = float(snr_prior)
        self.dwell_options = tuple(dwell_options)
        self.weights = weights or IndexWeights()

        self.detection = DetectionModel(
            p_fa=p_fa, n_eff=n_eff, slot_s=slot_s, retune_s=retune_s
        )
        # The probabilities the *actual* receiver delivers. These drive the Bayesian update and
        # the value term, and come from the scenario when one is available. ``self.detection``
        # stays the model used to price dwell length against coverage.
        self.detect_p_fa = float(p_fa if detect_p_fa is None else detect_p_fa)
        self.detect_p_d = float(
            self.detection.p_d(dwell_options[0], snr_prior) if detect_p_d is None else detect_p_d
        )
        self.deadlines = RevisitDeadlines(
            deadlines_s=np.full(num_bands, float(deadline_s)),
            slot_s=slot_s,
            trigger_dither=trigger_dither,
        )
        self.belief = OccupancyBelief(num_bands, p01=p01, p10=p10)

        # Slow loop. The kernels are refreshed every ``kernel_refresh_steps``, deliberately off
        # the per-decision critical path, so NFR-002's 50 ms budget is untouched by them.
        self.learn_kernels = bool(learn_kernels)
        self.kernel_refresh_steps = int(kernel_refresh_steps)
        self.kernels = KernelEstimator(
            num_bands,
            p_d=self.detect_p_d,
            p_fa=self.detect_p_fa,
            p01_prior=p01,
            p10_prior=p10,
        )
        self._steps_observed = 0

        # Computed once at construction so an oversubscribed receiver is loud rather than silent.
        self.feasibility = self.deadlines.feasibility(
            bandwidth_k=self.bandwidth_k, dwell_s=slot_s, retune_s=retune_s
        )

        if not 0.0 <= rho_min <= 1.0:
            raise ValueError(f"rho_min must lie in [0, 1], got {rho_min}")
        if not 0.0 <= rho_max <= 1.0:
            raise ValueError(f"rho_max must lie in [0, 1], got {rho_max}")
        if rho_min > rho_max:
            raise ValueError(f"rho_min {rho_min} exceeds rho_max {rho_max}")
        self.rho_min = float(rho_min)
        self.rho_max = float(rho_max)
        self.floor = CTMCFloorAgent(
            num_bands, mean_dwell_slots=floor_mean_dwell_slots, rng=self.rng
        )
        self.floor_confidence_threshold = float(floor_confidence_threshold)
        self.floor_draws = 0
        self.last_source = "index"

        # One coverage cycle minus the slot being served. With K bands at a time it takes this
        # many slots to clear a full set of simultaneous expiries, so the override has to fire
        # that far ahead or the last band in the queue lands past its deadline.
        self._queue_lookahead = max(0, math.ceil(num_bands / self.bandwidth_k) - 1)

        self.time_since_last_scan = np.zeros(num_bands, dtype=np.int64)
        self.revisit_counts = np.zeros(num_bands, dtype=np.int64)
        self.last_bands: list[int] = []
        self.last_dwell: int = self.dwell_options[0]
        self.last_breakdown: dict[str, float] = {}
        self._previous_start = 0

    @classmethod
    def from_scenario(cls, scenario: dict, **overrides) -> "IndexAgent":
        """Build an agent that matches the receiver it will actually be driving.

        The first end-to-end comparison ran with default receiver parameters against a scenario
        that specified its own, so the belief update used a false-alarm rate two orders of
        magnitude too small. A belief updated through the wrong ROC is confidently wrong, and the
        value term went flat. Deriving both from the scenario is the fix.
        """
        receiver = dict(scenario.get("receiver") or {})
        num_bands = int(scenario["bands"])
        step_ms = float(receiver.get("step_ms", 10.0))
        tuning_delay_ms = float(receiver.get("tuning_delay_ms", 0.0))
        bandwidth_k = int(receiver.get("bandwidth_k", 1))

        slot_s = step_ms / 1000.0
        retune_s = tuning_delay_ms / 1000.0

        # The environment detector is a Gaussian test on a single observation: the statistic is
        # N(snr_mean * snr_gain, sigma) when the band is active and N(0, sigma) when it is not,
        # compared against a fixed threshold (ml/environments/receiver.py). Charging the retune
        # here is the conservative reading, since a step that retuned integrates for less of its
        # slot.
        sigma = float(receiver.get("noise_sigma", 1.0))
        threshold = float(receiver.get("threshold", 1.5))
        snr_mean = float(receiver.get("snr_mean", 3.0))
        observe_ms = max(0.0, step_ms - tuning_delay_ms)
        snr_gain = math.sqrt(observe_ms / step_ms) if step_ms > 0 else 0.0

        derived = dict(
            bandwidth_k=bandwidth_k,
            slot_s=slot_s,
            retune_s=retune_s,
            detect_p_fa=float(norm.sf(threshold / sigma)),
            detect_p_d=float(norm.sf((threshold - snr_mean * snr_gain) / sigma)),
        )
        if "deadline_s" not in overrides:
            cycle = math.ceil(num_bands / bandwidth_k) * (slot_s + retune_s)
            derived["deadline_s"] = cycle / COVERAGE_BUDGET
        derived.update(overrides)
        return cls(num_bands, **derived)

    @property
    def deadline_slots(self) -> np.ndarray:
        return self.deadlines.deadline_slots

    # -- lifecycle -----------------------------------------------------------------------------

    def start_episode(self, episode: int = 0) -> None:
        self.kernels.reset()
        self._steps_observed = 0
        self._apply_kernels()
        self.floor.start_episode(episode)
        self.floor_draws = 0
        self.last_source = "index"
        self.time_since_last_scan[:] = 0
        self.revisit_counts[:] = 0
        self.belief.belief[:] = self.belief.stationary
        self.last_bands = []
        self.last_breakdown = {}
        self._previous_start = 0

    # -- decision ------------------------------------------------------------------------------

    def effective_belief(self, observation: np.ndarray) -> np.ndarray:
        """Occupancy belief fused with Ai-ml-2 periodicity prediction, weighted by confidence.

        ``periodicity_phase`` is the fraction of the estimated period elapsed since the last
        detection, so due-ness is *circular*: the emitter is likely on us near phase 0 and near
        phase 1, and pointing elsewhere in between. ``0.5 * (1 + cos(2 pi phase))`` is that bump,
        and it is what a von Mises prior over the illumination window reduces to.

        Confidence does the blending, so a low-confidence estimate changes nothing. The Ai-ml-2
        contract is explicit that a confident-but-wrong periodicity claim is worse than no claim,
        and this is the consumer side of that promise.
        """
        block = self._band_block(observation)
        phase = block[:, _PHASE_FEATURE]
        confidence = np.clip(block[:, _CONFIDENCE_FEATURE], 0.0, 1.0)
        due = 0.5 * (1.0 + np.cos(2.0 * np.pi * phase))
        return np.clip((1.0 - confidence) * self.belief.belief + confidence * due, 0.0, 1.0)

    def exploration_rate(self, observation: np.ndarray) -> float:
        """Fraction of looks currently drawn from the randomised floor.

        The rate *is* the fraction of the spectrum still uncharacterised, clipped into
        ``[rho_min, rho_max]``. A cold start with no prior intelligence -- the SIH26055 opening
        condition -- spends every look on the floor; twelve of sixteen bands modelled leaves a
        quarter discretionary; a fully modelled spectrum falls to ``rho_min`` and never to zero,
        because the worst-case bound has to hold for the whole mission rather than only its
        opening.

        An earlier rule annealed on *mean* periodicity confidence instead. On scenario B that mean
        plateaued near 0.22, because most emitters there are not cleanly periodic and the estimator
        is deliberately conservative about saying otherwise, so the floor took 61% of every
        episode's looks for ever and the index was overridden by uninformed randomness most of the
        time. Tying the rate to the same quantity that decides *where* the floor looks removed a
        tuning constant and the failure with it.
        """
        uncharacterised = len(self._uncharacterised_bands(observation))
        fraction = uncharacterised / self.num_bands
        return float(min(max(fraction, self.rho_min), self.rho_max))

    def select_action(self, observation: np.ndarray, explore: bool = True) -> int:
        threat = self._threat_from(observation)
        dwell = best_dwell(self.detection, self.snr_prior, self.dwell_options)
        p_d = np.full(self.num_bands, self.detect_p_d)

        inputs = IndexInputs(
            threat=threat,
            belief=self.effective_belief(observation),
            p_d=p_d,
            ident_credit=np.ones(self.num_bands),
            info_gain=self.belief.information_gain(p_d=p_d, p_fa=self.detect_p_fa),
            novelty=np.zeros(self.num_bands),
            elapsed_s=self._elapsed_for(dwell),
            pressure=self.deadlines.pressure(self.time_since_last_scan),
        )

        index = compute_index(inputs, self.weights)

        # The randomised floor. Drawn before the deadline override, never after: coverage
        # outranks exploration, and an overdue band is served on a floor step too.
        #
        # Deliberately NOT gated on ``explore``. That flag exists so an epsilon-greedy learner
        # can be evaluated greedily, and the floor is not exploration -- it is the structural
        # guarantee from Clarkson & Pollington that bounds worst-case behaviour against an emitter
        # no model predicts. Gating it here switched it off for every evaluation run, which in the
        # synchronisation-trap scenario was the difference between intercepting the emitter and
        # reporting a flawless sweep at a probability of detection of exactly zero.
        rho = self.exploration_rate(observation)
        if rho > 0.0 and self.rng.random() < rho:
            self.floor_draws += 1
            self.last_source = "floor"
            self.floor.set_candidates(self._uncharacterised_bands(observation))
            drawn = int(self.floor.select_action(observation))
            start, bands = drawn, [
                (drawn + offset) % self.num_bands for offset in range(self.bandwidth_k)
            ]
        else:
            self.last_source = "index"
            start, bands = select_window(index, self.bandwidth_k, self.mode)

        bands = apply_deadline_override(
            bands,
            self.deadlines.overdue(
                self.time_since_last_scan,
                lookahead=self._queue_lookahead,
                revisit_counts=self.revisit_counts,
            ),
            self.bandwidth_k,
        )
        # The contract's action is a single band; the receiver covers K from there. When the
        # override changes the set, the first forced band leads.
        start = bands[0]

        self.last_bands = list(bands)
        self.last_dwell = dwell
        self.last_breakdown = self._breakdown_for(inputs, start)
        self._previous_start = start
        return int(start)

    def observe(self, info: dict) -> None:
        """Fold one executed dwell back into the belief and the staleness counters.

        Called by ``ml/evaluation/runner.py`` with the environment's ``info`` dict. This is the
        "trained based on hits and misses" path: a miss updates the belief exactly as a hit does,
        through the same ROC.
        """
        scanned = [int(b) for b in info.get("scanned_bands", [])]
        detected = {int(b) for b in info.get("detected_bands", [])}

        self.belief.predict()
        self.time_since_last_scan += 1
        if scanned:
            outcomes = [b in detected for b in scanned]
            self.belief.correct(
                bands=scanned,
                detections=outcomes,
                p_d=self.detect_p_d,
                p_fa=self.detect_p_fa,
            )
            self.time_since_last_scan[scanned] = 0
            self.revisit_counts[scanned] += 1
            # The environment's info dict carries no timestamp, so the agent keeps its own. The
            # estimator only needs gaps between looks at the same band, and a step counter gives
            # exactly that.
            self.kernels.observe(self._steps_observed, scanned, outcomes)

        self._steps_observed += 1
        if (
            self.learn_kernels
            and self.kernel_refresh_steps > 0
            and self._steps_observed % self.kernel_refresh_steps == 0
        ):
            self._apply_kernels()

    def _apply_kernels(self) -> None:
        """Hand the learned transition kernels to the occupancy belief.

        Called only from the slow loop and from ``start_episode``. An unobserved band keeps the
        prior, because ``KernelEstimator`` blends toward it until enough looks have accumulated.
        """
        if not self.learn_kernels:
            return
        p01, p10 = self.kernels.kernels()
        self.belief.p01 = p01
        self.belief.p10 = p10

    # -- helpers -------------------------------------------------------------------------------

    def characterisation(self, observation: np.ndarray) -> np.ndarray:
        """How well each band is understood, in [0, 1].

        The better of two things: how much evidence the occupancy-kernel estimate rests on, and
        how confident the periodicity estimator is. Evidence is the load-bearing half. Periodicity
        confidence only rises for cleanly periodic emitters, so on its own it marks a band holding
        a random emitter as unknown for ever -- and an *empty* band too, though an empty band is
        the most thoroughly characterised thing in the spectrum. Scoring empty bands as unknown
        sent the floor's discretionary looks to the one place with nothing to find, and cost 72 to
        89% of every episode.
        """
        periodicity = np.clip(self._band_block(observation)[:, _CONFIDENCE_FEATURE], 0.0, 1.0)
        return np.maximum(self.kernels.evidence_confidence(), periodicity)

    def _uncharacterised_bands(self, observation: np.ndarray) -> list[int]:
        """Bands not yet understood well enough to stop spending random looks on them.

        The floor exists for what is not yet modelled, so pointing it at the whole spectrum wastes
        discretionary looks on bands the index already handles. Measured on scenario B, leaving it
        untargeted cost about 7% of run intercept rate against round-robin.

        Both degenerate cases resolve toward looking rather than not looking. An empty list is
        returned when *everything* is understood, and ``CTMCFloorAgent.set_candidates`` reads that
        as the whole spectrum: understanding the spectrum is never a reason to stop watching it.
        """
        known = self.characterisation(observation)
        return [int(b) for b in np.nonzero(known < self.floor_confidence_threshold)[0]]

    def _band_block(self, observation: np.ndarray) -> np.ndarray:
        """The per-band feature matrix, from the observation vector documented layout.

        Features are looked up through ``BAND_FEATURES`` rather than hard-coded offsets, so a
        change to the feature order in ``ml/environments/state.py`` cannot silently mis-align
        this.
        """
        observation = np.asarray(observation, dtype=np.float64)
        return observation[: NUM_BAND_FEATURES * self.num_bands].reshape(
            self.num_bands, NUM_BAND_FEATURES
        )

    def _threat_from(self, observation: np.ndarray) -> np.ndarray:
        return np.clip(self._band_block(observation)[:, _PRIORITY_FEATURE], 0.0, 1.0)

    def _elapsed_for(self, dwell: int) -> np.ndarray:
        """Wall time each band would cost, charging retune only where the receiver has to move."""
        elapsed = np.full(self.num_bands, dwell * self.slot_s + self.retune_s)
        elapsed[self._previous_start] = dwell * self.slot_s
        return elapsed

    def _breakdown_for(self, inputs: IndexInputs, band: int) -> dict[str, float]:
        terms = compute_index(inputs, self.weights, breakdown=True)
        return {name: float(values[band]) for name, values in terms.items()}

    def describe(self) -> dict:
        return {
            "policy_type": self.policy_type,
            "num_bands": self.num_bands,
            "bandwidth_k": self.bandwidth_k,
            "mode": self.mode,
            "dwell_options": list(self.dwell_options),
            "deadline_slots": int(self.deadline_slots.max()),
            "trigger_dither": self.deadlines.trigger_dither,
            "feasible": bool(self.feasibility.feasible),
            "detect_p_d": self.detect_p_d,
            "detect_p_fa": self.detect_p_fa,
            "learn_kernels": self.learn_kernels,
            "kernel_refresh_steps": self.kernel_refresh_steps,
            "rho_min": self.rho_min,
            "rho_max": self.rho_max,
            "floor_confidence_threshold": self.floor_confidence_threshold,
            **{
                name: getattr(self.weights, name)
                for name in ("w_value", "w_info", "w_novelty", "w_deadline")
            },
        }
