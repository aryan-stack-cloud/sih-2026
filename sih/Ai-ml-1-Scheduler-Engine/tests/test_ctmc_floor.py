"""The randomised floor (SCT solution spec Section 7), and baseline arm B4.

Clarkson & Pollington proved that against emitters with unknown parameters, no deterministic
search strategy beats a random one. SIH26055 is explicitly that regime, so the correct engineering
response is not to argue with the theorem but to carry the random strategy as a floor and let
learning operate strictly above it.

El-Mahassni & Howard's continuous-time Markov chain is the particular random strategy to carry:
its expected intercept time approaches linearity in the emitter's scan period fastest and
*smoothly*, without the abrupt spikes a deterministic sweep shows at rational period ratios.

The last two tests are the argument in one place. A periodic sweep is usually better than random
and occasionally infinite. The floor is never better and never catastrophic.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.ctmc_floor import CTMCFloorAgent
from ml.agents.factory import build_agent

N = 8


def agent(seed: int = 0, **kwargs) -> CTMCFloorAgent:
    a = CTMCFloorAgent(N, rng=np.random.default_rng(seed), **kwargs)
    a.start_episode()
    return a


def schedule(a: CTMCFloorAgent, steps: int) -> list[int]:
    obs = np.zeros(1)
    return [int(a.select_action(obs)) for _ in range(steps)]


# -- shape ---------------------------------------------------------------------------------------

def test_it_reports_the_ctmc_policy_type():
    assert agent().policy_type == "ctmc"


def test_the_factory_builds_it_from_the_contract_policy_name():
    assert isinstance(build_agent("ctmc", num_bands=N), CTMCFloorAgent)


def test_every_action_is_a_real_band():
    assert all(0 <= b < N for b in schedule(agent(), 500))


# -- the chain -----------------------------------------------------------------------------------

def test_it_visits_every_band_about_equally_often():
    """A uniform stationary distribution is what makes the worst-case bound hold for every band."""
    counts = np.bincount(schedule(agent(), 40_000), minlength=N)
    assert counts.min() > 0.8 * counts.mean()
    assert counts.max() < 1.2 * counts.mean()


def test_a_longer_mean_sojourn_produces_longer_runs_on_one_band():
    brief = schedule(agent(seed=1, mean_dwell_slots=1.0), 4000)
    sticky = schedule(agent(seed=1, mean_dwell_slots=6.0), 4000)
    assert _mean_run_length(sticky) > 2.0 * _mean_run_length(brief)


def test_the_mean_sojourn_is_about_what_was_asked_for():
    runs = _mean_run_length(schedule(agent(seed=2, mean_dwell_slots=4.0), 20_000))
    assert runs == pytest.approx(4.0, rel=0.2)


def _mean_run_length(bands: list[int]) -> float:
    runs, current = [], 1
    for previous, band in zip(bands, bands[1:]):
        if band == previous:
            current += 1
        else:
            runs.append(current)
            current = 1
    runs.append(current)
    return float(np.mean(runs))


# -- reproducibility -------------------------------------------------------------------------------

def test_the_same_seed_gives_the_same_schedule():
    assert schedule(agent(seed=5), 200) == schedule(agent(seed=5), 200)


def test_different_seeds_give_different_schedules():
    assert schedule(agent(seed=5), 200) != schedule(agent(seed=6), 200)


# -- restriction to uncharacterised bands ----------------------------------------------------------

def test_it_can_be_restricted_to_the_bands_we_know_least_about():
    """The floor's job is the unknown, so the index keeps the bands it has already modelled."""
    a = agent(seed=3)
    a.set_candidates([2, 5])
    assert set(schedule(a, 300)) == {2, 5}


def test_restricting_to_one_band_stays_on_it():
    a = agent(seed=3)
    a.set_candidates([4])
    assert set(schedule(a, 50)) == {4}


def test_clearing_the_restriction_returns_to_the_whole_spectrum():
    a = agent(seed=3)
    a.set_candidates([2])
    schedule(a, 10)
    a.set_candidates(None)
    assert len(set(schedule(a, 2000))) == N


def test_an_empty_candidate_set_falls_back_to_the_whole_spectrum():
    """Every band characterised is not a reason to stop looking."""
    a = agent(seed=3)
    a.set_candidates([])
    assert len(set(schedule(a, 2000))) == N


# -- the argument ----------------------------------------------------------------------------------

def _first_intercept(bands: list[int], period: int, illum: int, phase: int, target: int = 0):
    """First step at which the schedule is on the emitter's band while it is illuminating."""
    for t, band in enumerate(bands):
        if band == target and (t - phase) % period < illum:
            return t
    return None


def test_a_periodic_sweep_can_be_locked_out_for_ever():
    """The premise. Sweep period 8 against scan period 8 visits exactly one emitter phase."""
    sweep = [t % N for t in range(20_000)]
    assert _first_intercept(sweep, period=N, illum=1, phase=3) is None


def test_the_floor_intercepts_the_emitter_that_locks_out_the_sweep():
    """The conclusion. Never better than a tuned schedule, never catastrophic either."""
    got = _first_intercept(schedule(agent(seed=9), 20_000), period=N, illum=1, phase=3)
    assert got is not None


def test_the_floor_intercepts_across_every_scan_period_including_the_commensurate_ones():
    """Smooth, not spiky. The sweep fails on the periods that divide it; the floor fails on none."""
    bands = schedule(agent(seed=4), 60_000)
    sweep = [t % N for t in range(60_000)]

    floor_times, sweep_failures = [], 0
    for period in (5, 8, 12, 16, 24, 32, 40, 64):
        floor_hit = _first_intercept(bands, period=period, illum=1, phase=3)
        assert floor_hit is not None, f"floor failed at scan period {period}"
        floor_times.append(floor_hit)
        if _first_intercept(sweep, period=period, illum=1, phase=3) is None:
            sweep_failures += 1

    assert sweep_failures > 0, "the periodic sweep should be locked out on commensurate periods"
    assert max(floor_times) < 40 * max(1, min(floor_times))
