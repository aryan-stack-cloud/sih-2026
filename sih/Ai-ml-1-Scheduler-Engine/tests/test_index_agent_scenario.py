"""Making the index's value term real: scenario-derived sensing, and periodicity fusion.

Two defects the first end-to-end comparison exposed, both of which flattened the value term until
the index behaved like a slightly worse round-robin.

1. The agent used a default detection model instead of the receiver it was actually driving, so
   its Bayesian update ran on the wrong Pd and a Pfa two orders of magnitude too small. A belief
   updated through the wrong ROC is confidently wrong.
2. It ignored ``periodicity_phase`` and ``periodicity_confidence`` entirely -- the very features
   the headline scenario exists to reward, and the ones Ai-ml-2 is built to supply.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.index_agent import IndexAgent
from ml.environments.state import BAND_FEATURES, StateBuilder
from ml.utils.config import load_scenario

N = 16
PHASE = BAND_FEATURES.index("periodicity_phase")
CONFIDENCE = BAND_FEATURES.index("periodicity_confidence")


class _Receiver:
    tuned_start = 0
    dwell_remaining_ms = 0
    tuning_delay_countdown_ms = 0

    def tuned_bands(self, k, n):
        return [(self.tuned_start + i) % n for i in range(k)]


def observation(phase=None, confidence=None) -> np.ndarray:
    sb = StateBuilder(N)
    sb.update([], [], _Receiver(), 1)
    if phase is not None:
        sb.periodicity_phase = np.asarray(phase, dtype=np.float32)
    if confidence is not None:
        sb.periodicity_confidence = np.asarray(confidence, dtype=np.float32)
    return sb.to_vector()


# -- scenario-derived sensing ----------------------------------------------------------------------

def test_it_takes_its_receiver_parameters_from_the_scenario():
    a = IndexAgent.from_scenario(load_scenario("B"))
    assert a.bandwidth_k == 2
    assert a.slot_s == pytest.approx(0.010)
    assert a.retune_s == pytest.approx(0.003)


def test_it_derives_the_detection_probabilities_the_receiver_actually_delivers():
    """threshold 1.5, noise sigma 1.0, snr_mean 3.0, 7 of 10 ms observed after a retune."""
    a = IndexAgent.from_scenario(load_scenario("B"))
    assert a.detect_p_fa == pytest.approx(0.0668, abs=2e-3)
    assert a.detect_p_d == pytest.approx(0.8438, abs=5e-3)


def test_the_derived_deadline_leaves_room_for_value_seeking():
    """A deadline equal to the coverage cycle is round-robin with extra steps."""
    a = IndexAgent.from_scenario(load_scenario("B"))
    assert a.feasibility.feasible
    assert 0.2 < a.feasibility.committed_fraction <= 0.7


def test_an_explicit_deadline_overrides_the_derived_one():
    a = IndexAgent.from_scenario(load_scenario("B"), deadline_s=0.5)
    assert a.deadline_slots.max() == 50


def test_the_belief_update_uses_the_scenario_false_alarm_rate():
    """A Pfa of 1e-3 against a receiver delivering 6.7e-2 makes every detection look conclusive."""
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    a.belief.belief[:] = 0.5
    a.observe({"scanned_bands": [0], "detected_bands": [0]})
    # With Pd 0.844 and Pfa 0.0668 the posterior is 0.927, not the 0.999 a 1e-3 Pfa would give.
    assert float(a.belief.belief[0]) == pytest.approx(0.927, abs=0.01)


# -- periodicity fusion ------------------------------------------------------------------------------
#
# Ai-ml-2's hits-and-misses fit anchors phase 0 at the START of the fitted illuminated window, so a
# periodic emitter is on for phase in [0, duty) and quiet until the cycle wraps. Phase near 1 means
# about due -- not on.

def test_a_band_whose_window_has_just_opened_is_covered_by_the_chosen_window():
    """Phase just past 0 means the window has opened; phase near 0.5 means it is long closed.

    Scenario B gives the receiver two bands of instantaneous bandwidth, so the action names a
    window start and the assertion is about what the window covers, not what it starts on.
    """
    a = IndexAgent.from_scenario(load_scenario("B"), deadline_s=10.0)
    a.start_episode()
    phase = np.full(N, 0.5)
    phase[6] = 0.01
    confidence = np.full(N, 0.9)
    a.select_action(observation(phase, confidence))
    assert 6 in a.last_bands


def test_a_band_whose_window_is_about_to_open_is_not_yet_rated_on():
    """The stretch just before a window opens is quiet, however due the band is.

    The cosine this replaced was symmetric about phase 0, written for a stand-in whose phase
    counted from the last detection. Against Ai-ml-2's phase it rated 0.95 exactly as on as 0.05,
    and on scenario B the index spent more looks before windows opened than inside them.
    """
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    a.belief.belief[:] = 0.0
    phase = np.full(N, 0.02)
    phase[1] = 0.95
    fused = a.effective_belief(observation(phase, np.ones(N)))
    assert float(fused[0]) > 0.9
    assert float(fused[1]) == pytest.approx(0.0)


def test_the_window_start_is_rated_above_the_middle_of_the_cycle():
    a = IndexAgent.from_scenario(load_scenario("B"), deadline_s=10.0)
    a.start_episode()
    fused_at_zero = a.effective_belief(observation(np.zeros(N), np.ones(N)))
    fused_mid = a.effective_belief(observation(np.full(N, 0.5), np.ones(N)))
    assert float(fused_at_zero[0]) > float(fused_mid[0])


def _look(agent, band, phase, detected, confidence=0.9):
    """One look at ``band`` taken while every band sat at ``phase`` under a periodicity claim."""
    agent.select_action(observation(np.full(N, phase), np.full(N, confidence)))
    agent.observe({"scanned_bands": [band], "detected_bands": [band] if detected else []})


def test_the_window_width_is_learned_from_the_agents_own_hits_and_misses():
    """Ai-ml-2 fits a duty alongside period and phase but does not send it, so the agent infers it.

    Hits up to phase 0.17 and misses from 0.27 on pin this band's window near a fifth of the
    cycle: still open at 0.1, closed by 0.3. A band never looked at keeps the flat prior.
    """
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    for phase, detected in [(0.02, True), (0.12, True), (0.17, True),
                            (0.27, False), (0.35, False), (0.45, False)] * 2:
        _look(a, band=3, phase=phase, detected=detected)

    learned_open = float(a.window_occupancy(np.full(N, 0.1))[3])
    learned_closed = float(a.window_occupancy(np.full(N, 0.3))[3])
    prior_open = float(a.window_occupancy(np.full(N, 0.1))[10])
    prior_closed = float(a.window_occupancy(np.full(N, 0.3))[10])

    assert learned_open > 0.95
    assert learned_closed < 0.05
    assert learned_open > prior_open
    assert learned_closed < prior_closed


def test_looks_without_a_periodicity_claim_teach_nothing_about_the_window():
    """Below Ai-ml-2's claim threshold the phase is a placeholder, not a position in any cycle."""
    fresh = IndexAgent.from_scenario(load_scenario("B"))
    fresh.start_episode()
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    for phase in (0.05, 0.3, 0.6, 0.9):
        _look(a, band=3, phase=phase, detected=False, confidence=0.3)
        _look(a, band=3, phase=phase, detected=True, confidence=0.0)

    for phase in (0.0, 0.1, 0.3, 0.6):
        assert a.window_occupancy(np.full(N, phase)) == pytest.approx(
            fresh.window_occupancy(np.full(N, phase))
        )


def test_the_learned_window_does_not_carry_into_the_next_episode():
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    before = a.window_occupancy(np.full(N, 0.3)).copy()
    for _ in range(4):
        _look(a, band=3, phase=0.3, detected=False)
    assert float(a.window_occupancy(np.full(N, 0.3))[3]) < float(before[3])

    a.start_episode()
    assert a.window_occupancy(np.full(N, 0.3)) == pytest.approx(before)


def test_zero_confidence_leaves_the_occupancy_belief_untouched():
    """A confident-but-wrong periodicity claim is worse than no claim, so no confidence, no effect."""
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    a.belief.belief[:] = 0.42
    fused = a.effective_belief(observation(np.full(N, 0.99), np.zeros(N)))
    assert fused == pytest.approx(np.full(N, 0.42))


def test_full_confidence_hands_the_belief_to_the_periodicity_estimate():
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    a.belief.belief[:] = 0.0
    fused = a.effective_belief(observation(np.zeros(N), np.ones(N)))
    assert fused == pytest.approx(np.ones(N))


def test_partial_confidence_blends_the_two():
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    a.belief.belief[:] = 0.0
    fused = a.effective_belief(observation(np.zeros(N), np.full(N, 0.5)))
    assert fused == pytest.approx(np.full(N, 0.5))


def test_fusion_never_leaves_the_unit_interval():
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    for belief in (0.0, 0.5, 1.0):
        a.belief.belief[:] = belief
        for phase in (0.0, 0.25, 0.5, 0.75, 1.0):
            fused = a.effective_belief(observation(np.full(N, phase), np.full(N, 0.7)))
            assert np.all(fused >= 0.0) and np.all(fused <= 1.0)


# -- the guarantee survives all of it ----------------------------------------------------------------

def test_the_coverage_guarantee_still_holds_with_a_strong_value_signal():
    """A loud, confidently periodic band must not be allowed to monopolise the receiver.

    Band 3 sits at the start of its window for ever, hitting on every look, so nothing it learns
    about its window ever makes it quieter.
    """
    a = IndexAgent.from_scenario(load_scenario("B"))
    a.start_episode()
    phase = np.full(N, 0.5)
    phase[3] = 0.0
    confidence = np.full(N, 0.95)
    obs = observation(phase, confidence)

    worst = 0
    for _ in range(600):
        a.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": a.last_bands})
        worst = max(worst, int(a.time_since_last_scan.max()))
    assert worst <= int(a.deadline_slots.max())
