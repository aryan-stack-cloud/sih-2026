"""Detection model -- Pd, Pfa and the dwell decision (SCT solution spec Sections 2 and 4.3.1).

The problem statement asks for "Receiver Sensitivity and threshold detection performance" as a
figure of merit. That means Pd and Pfa must be *derived* from an operating point, not tuned to
make a slide look good. Fix Pfa, the threshold follows, and Pd follows from SNR along the ROC.

The tests that matter most are the last group. The optimal dwell is non-monotone in SNR, peaking
at marginal signal strength and falling away on both sides. Getting that wrong is what makes a
hand-tuned dwell rule waste receiver time digging for signals it cannot reach.
"""

from __future__ import annotations

import pytest

from ml.environments.detection_model import (
    DetectionModel,
    best_dwell,
    pfa_for_threshold,
    probability_of_detection,
    threshold_for_pfa,
)

PFA = 1e-3
N_EFF = 100  # effective independent integration samples per slot
SLOT_S = 0.010
RETUNE_S = 0.005


def model() -> DetectionModel:
    return DetectionModel(p_fa=PFA, n_eff=N_EFF, slot_s=SLOT_S, retune_s=RETUNE_S)


# -- the operating point ------------------------------------------------------------------------

def test_threshold_delivers_the_requested_false_alarm_rate():
    """Round-trip: the threshold set for a target Pfa must reproduce that Pfa."""
    for target in (1e-2, 1e-3, 1e-6):
        lam = threshold_for_pfa(target, n_s=400)
        assert pfa_for_threshold(lam, n_s=400) == pytest.approx(target, rel=1e-6)


def test_a_stricter_false_alarm_target_costs_detection_probability():
    loose = probability_of_detection(p_fa=1e-2, n_s=100, snr=0.3)
    strict = probability_of_detection(p_fa=1e-6, n_s=100, snr=0.3)
    assert strict < loose


def test_detection_probability_rises_with_integration_time():
    weak = probability_of_detection(p_fa=PFA, n_s=100, snr=0.2)
    strong = probability_of_detection(p_fa=PFA, n_s=800, snr=0.2)
    assert strong > weak


def test_detection_probability_rises_with_signal_strength():
    quiet = probability_of_detection(p_fa=PFA, n_s=100, snr=0.1)
    loud = probability_of_detection(p_fa=PFA, n_s=100, snr=1.0)
    assert loud > quiet


def test_detection_probability_stays_a_probability():
    for snr in (1e-6, 0.01, 0.5, 5.0, 100.0):
        p = probability_of_detection(p_fa=PFA, n_s=100, snr=snr)
        assert 0.0 <= p <= 1.0


def test_pd_matches_the_verified_reference_table():
    """Section 4.3.1's table, recomputed by docs/.../verify_solution_constants.py."""
    m = model()
    assert m.p_d(dwell_slots=1, snr=0.3) == pytest.approx(0.228, abs=2e-3)
    assert m.p_d(dwell_slots=2, snr=0.3) == pytest.approx(0.472, abs=2e-3)
    assert m.p_d(dwell_slots=4, snr=0.3) == pytest.approx(0.812, abs=2e-3)
    assert m.p_d(dwell_slots=8, snr=0.3) == pytest.approx(0.987, abs=2e-3)


# -- the dwell decision --------------------------------------------------------------------------

def test_dwell_value_is_a_rate_not_a_value():
    """Two slots that detect half as often as one slot must not score the same.

    This is the whole reason the index divides by elapsed time. Without it the scheduler cannot
    see that a detection costing eight slots is worth less than one costing a single slot.
    """
    m = model()
    one = m.value_rate(dwell_slots=1, snr=1.0)
    eight = m.value_rate(dwell_slots=8, snr=1.0)
    assert one > eight


def test_a_strong_signal_needs_only_one_slot():
    m = model()
    assert best_dwell(m, snr=1.0, options=(1, 2, 4, 8)) == 1


def test_a_marginal_signal_justifies_a_long_dwell():
    """At -10 dB integration is what lifts the signal over threshold, so eight slots pay."""
    m = model()
    assert best_dwell(m, snr=0.1, options=(1, 2, 4, 8)) == 8


def test_a_hopeless_signal_is_not_worth_a_long_dwell():
    """Below about -12 dB no available dwell reaches threshold, so stop spending coverage on it.

    This regime is what hand-tuned "weak signal means dwell longer" rules always get wrong.
    """
    m = model()
    assert best_dwell(m, snr=0.05, options=(1, 2, 4, 8)) == 1


def test_the_optimal_dwell_peaks_at_marginal_signal_strength():
    """Non-monotone in SNR: 1, then 8, then down through 4 and 2, back to 1."""
    m = model()
    curve = [best_dwell(m, snr=g, options=(1, 2, 4, 8)) for g in (0.05, 0.1, 0.2, 0.3, 0.5, 1.0)]
    assert curve == [1, 8, 4, 2, 1, 1]


def test_retune_cost_shifts_the_optimum_toward_longer_dwells():
    """When switching bands is expensive, staying put gets relatively cheaper."""
    cheap = DetectionModel(p_fa=PFA, n_eff=N_EFF, slot_s=SLOT_S, retune_s=0.0)
    dear = DetectionModel(p_fa=PFA, n_eff=N_EFF, slot_s=SLOT_S, retune_s=0.050)
    assert best_dwell(dear, snr=0.3, options=(1, 2, 4, 8)) >= best_dwell(
        cheap, snr=0.3, options=(1, 2, 4, 8)
    )


def test_dwell_options_must_not_be_empty():
    with pytest.raises(ValueError):
        best_dwell(model(), snr=0.3, options=())
