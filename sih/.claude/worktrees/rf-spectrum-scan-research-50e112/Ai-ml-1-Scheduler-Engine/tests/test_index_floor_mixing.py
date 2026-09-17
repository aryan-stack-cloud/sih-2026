"""Mixing the randomised floor into the index policy (SCT solution spec Section 7).

Clarkson & Pollington: against emitters with unknown parameters no deterministic strategy beats a
random one. The response is not to argue with the theorem but to carry the random strategy
permanently, so a fraction rho of every mission's looks is drawn from the CTMC floor.

That buys two things. A bounded worst case against an emitter no model predicts, and -- the reason
it matters for the demo -- an *aperiodic* visit pattern. A scheduler that settles into an exact
integer cycle is vulnerable to the same synchronisation lockout as a round-robin sweep, and it
cannot detect that it has happened.

rho anneals with the confidence the periodicity estimator reports, so a cold start with no prior
intelligence is nearly all floor and a well-modelled spectrum is nearly all index. It never
reaches zero: the guarantee has to hold for the whole mission, not only its opening.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.index_agent import IndexAgent
from ml.environments.state import StateBuilder

N = 16


class _Receiver:
    tuned_start = 0
    dwell_remaining_ms = 0
    tuning_delay_countdown_ms = 0

    def tuned_bands(self, k, n):
        return [(self.tuned_start + i) % n for i in range(k)]


def observation(confidence: float = 0.0) -> np.ndarray:
    sb = StateBuilder(N)
    sb.update([], [], _Receiver(), 1)
    sb.periodicity_confidence = np.full(N, confidence, dtype=np.float32)
    return sb.to_vector()


def agent(seed: int = 0, **kwargs) -> IndexAgent:
    defaults = dict(num_bands=N, bandwidth_k=1, deadline_s=10.0, slot_s=0.010, retune_s=0.005)
    defaults.update(kwargs)
    a = IndexAgent(rng=np.random.default_rng(seed), **defaults)
    a.start_episode()
    return a


def drive(a: IndexAgent, steps: int, confidence: float = 0.0) -> list[int]:
    obs = observation(confidence)
    out = []
    for _ in range(steps):
        out.append(int(a.select_action(obs)))
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
    return out


# -- the mixing rate ------------------------------------------------------------------------------

def test_a_zero_floor_never_leaves_the_index():
    a = agent(rho_min=0.0, rho_max=0.0)
    drive(a, 300)
    assert a.floor_draws == 0


def test_the_floor_fires_at_about_the_configured_rate():
    a = agent(seed=1, rho_min=0.25, rho_max=0.25)
    drive(a, 4000)
    assert a.floor_draws / 4000 == pytest.approx(0.25, abs=0.03)


def test_the_floor_is_reported_so_a_demo_can_show_when_it_fired():
    a = agent(seed=1, rho_min=1.0)
    a.select_action(observation())
    assert a.last_source == "floor"

    b = agent(seed=1, rho_min=0.0, rho_max=0.0)
    b.select_action(observation())
    assert b.last_source == "index"


# -- annealing -------------------------------------------------------------------------------------

def test_a_cold_start_with_no_confidence_is_nearly_all_floor():
    a = agent(rho_min=0.1)
    assert a.exploration_rate(observation(confidence=0.0)) > 0.9


def test_a_confidently_modelled_spectrum_falls_back_toward_the_floor_minimum():
    a = agent(rho_min=0.1)
    assert a.exploration_rate(observation(confidence=1.0)) < 0.1 + 0.05


def test_the_floor_never_anneals_to_zero():
    """The bound has to hold for the whole mission, not only its opening."""
    a = agent(rho_min=0.1)
    assert a.exploration_rate(observation(confidence=1.0)) >= 0.1


def test_annealing_is_monotone_in_confidence():
    a = agent(rho_min=0.1)
    rates = [a.exploration_rate(observation(confidence=c)) for c in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert all(later <= earlier for earlier, later in zip(rates, rates[1:]))


# -- the guarantees the floor must not break -------------------------------------------------------

def test_an_oversubscribed_deadline_is_reported_rather_than_silently_missed():
    """16 bands at K=1 need a 240 ms cycle. A 200 ms deadline is arithmetic, not effort.

    The system must say so. Silently missing the deadline is the failure this design replaces.
    """
    a = agent(deadline_s=0.200)
    assert not a.feasibility.feasible
    assert a.feasibility.required_bandwidth_k > 1
    assert "infeasible" in a.feasibility.message.lower()


def test_the_floor_never_overrides_a_deadline():
    """Coverage outranks exploration. An overdue band is served even on a floor step."""
    a = agent(seed=2, rho_min=1.0, deadline_s=0.400)  # 40 slots, cycle is 24
    assert a.feasibility.feasible
    worst = 0
    obs = observation()
    for _ in range(600):
        a.select_action(obs)
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
        worst = max(worst, int(a.time_since_last_scan.max()))
    assert worst <= int(a.deadline_slots.max())


def test_the_floor_still_reports_a_breakdown():
    """The decomposition panel must not go blank on floor steps."""
    a = agent(seed=3, rho_min=1.0)
    a.select_action(observation())
    assert set(a.last_breakdown) == {"value", "information", "novelty", "deadline", "elapsed_s"}


# -- the anti-lockout property ---------------------------------------------------------------------

def test_mixing_the_floor_breaks_an_exact_integer_visit_cycle():
    """A scheduler that settles into a fixed cycle inherits the sweep's lockout.

    Band 0 is checked against an emitter with an 8-step scan period illuminating for one step at
    phase 3 -- the configuration that a stride-1 round-robin over 8 bands can never intercept.
    """
    sweep = [t % 8 for t in range(4000)]
    assert _would_intercept(sweep, period=8, illum=1, phase=3) is False

    a = IndexAgent(
        num_bands=8, bandwidth_k=1, deadline_s=0.200, slot_s=0.010, retune_s=0.005,
        rho_min=0.15, rho_max=0.15, rng=np.random.default_rng(4),
    )
    a.start_episode()
    obs_8 = _observation_for(8)
    visits = []
    for _ in range(4000):
        visits.append(int(a.select_action(obs_8)))
        a.observe({"scanned_bands": a.last_bands, "detected_bands": []})
    assert _would_intercept(visits, period=8, illum=1, phase=3) is True


def _observation_for(num_bands: int) -> np.ndarray:
    sb = StateBuilder(num_bands)
    sb.update([], [], _Receiver(), 1)
    return sb.to_vector()


def _would_intercept(visits: list[int], period: int, illum: int, phase: int, band: int = 0) -> bool:
    return any(
        v == band and (t - phase) % period < illum for t, v in enumerate(visits)
    )
