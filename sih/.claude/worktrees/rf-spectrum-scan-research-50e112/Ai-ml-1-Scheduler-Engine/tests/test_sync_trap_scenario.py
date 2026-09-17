"""The synchronisation trap, end to end (solution spec Section 6 and Section 11.3 scenario S1).

The failure open loop cannot see in itself. A receiver sweeping 8 bands one at a time visits band
b at every step where ``t mod 8 == b``. An emitter in that band illuminating for one step every 8
at phase 3 is visible only at ``t mod 8 == 3``. Unless the emitter happens to sit in band 3, those
two sets never meet: the sweep runs flawlessly, reports a probability of detection of zero, and
looks exactly like a receiver watching an empty band.

This is not a contrived edge case. Clarkson's own worked example has an emitter invisible to a
1 s sweep until the dwell in its band is raised past 400 ms, and Winsor & Hughes measured the
signature: a channel sweep whose probability of intercept was flat in observation period, because
extra time bought nothing.

Expressing it needs one thing the emitter builder did not have, a way to pin an emitter to a
chosen band, so the first half of this file covers that.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.agents.factory import build_agent
from ml.agents.index_agent import IndexAgent
from ml.environments.emitters import build_emitters
from ml.environments.environment import make_env
from ml.evaluation.runner import run_episode

TRAP = {
    "scenario_id": "B",
    "name": "Synchronisation trap",
    "bands": 8,
    "emitters": 1,
    "duration_steps": 800,
    "seed": 7,
    "emitter_mix": {"periodic": 1.0},
    "high_priority_fraction": 1.0,
    # Scan period 8 against a stride-1 sweep over 8 bands, illuminating one step in eight.
    "emitter_params": {"periodic": {"period": 8, "on_duration": 1, "phase": 3, "band": 5}},
    "receiver": {
        "bandwidth_k": 1,
        "dwell_ms": 4,
        "tuning_delay_ms": 0,
        "step_ms": 10,
        "threshold": 1.5,
        "snr_mean": 6.0,
        "noise_sigma": 0.3,
    },
}


# -- pinning an emitter to a band ----------------------------------------------------------------

def test_a_pinned_band_is_honoured():
    emitters = build_emitters(
        1, 8, {"periodic": 1.0}, np.random.default_rng(0), params_by_class={"periodic": {"band": 5}}
    )
    assert emitters[0].bands == (5,)


def test_pinning_is_stable_across_seeds():
    """The whole point: the trap must not depend on which band the dice chose."""
    for seed in range(6):
        emitters = build_emitters(
            1, 8, {"periodic": 1.0}, np.random.default_rng(seed),
            params_by_class={"periodic": {"band": 5}},
        )
        assert emitters[0].bands == (5,)


def test_an_unpinned_emitter_still_gets_a_random_band():
    seen = {
        build_emitters(1, 8, {"periodic": 1.0}, np.random.default_rng(s))[0].bands
        for s in range(30)
    }
    assert len(seen) > 1


def test_a_band_outside_the_spectrum_is_rejected():
    with pytest.raises(ValueError):
        build_emitters(
            1, 8, {"periodic": 1.0}, np.random.default_rng(0),
            params_by_class={"periodic": {"band": 99}},
        )


def test_an_agile_emitters_hop_set_can_be_pinned():
    emitters = build_emitters(
        1, 8, {"agile": 1.0}, np.random.default_rng(0),
        params_by_class={"agile": {"bands": [1, 6]}},
    )
    assert set(emitters[0].bands) == {1, 6}


# -- the trap itself ---------------------------------------------------------------------------------

def _run(agent, seed: int = 7):
    env = make_env(TRAP, seed=seed)
    metrics = run_episode(env, agent, seed=seed)
    return metrics


def test_the_emitter_really_is_active_in_this_scenario():
    """Guard against the trap passing for the trivial reason that nothing ever transmits."""
    env = make_env(TRAP, seed=7)
    env.reset(seed=7)
    assert env.ground_truth.occupancy.sum() > 50


def test_a_round_robin_sweep_is_locked_out_completely():
    """The premise. A flawless sweep, and not one detection in 800 steps."""
    sweep = build_agent("baseline", TRAP["bands"], {"stride": 1, "mode": "round_robin"})
    metrics = _run(sweep)
    assert metrics.pd == pytest.approx(0.0, abs=1e-9)


def test_the_locked_out_sweep_never_even_sees_the_emitter_once():
    """Interception ratio 0.0 in 800 steps. Not late, not rare: never."""
    sweep = build_agent("baseline", TRAP["bands"], {"stride": 1, "mode": "round_robin"})
    assert _run(sweep).interception_ratio == pytest.approx(0.0)


def test_the_index_scheduler_intercepts_the_same_emitter():
    """The conclusion. Same spectrum, same seed, same receiver."""
    metrics = _run(IndexAgent.from_scenario(TRAP))
    assert metrics.pd > 0.05
    assert metrics.interception_ratio == pytest.approx(1.0)


def test_the_randomised_floor_alone_also_escapes_the_lockout():
    """Clarkson & Pollington: against an unknown emitter, random is already enough."""
    floor = build_agent("ctmc", TRAP["bands"], rng=np.random.default_rng(3))
    metrics = _run(floor)
    assert metrics.pd > 0.05
    assert metrics.interception_ratio == pytest.approx(1.0)


def test_the_index_escapes_the_lockout():
    """The claim. Not that the index is best here, only that it is not blind."""
    metrics = _run(IndexAgent.from_scenario(TRAP))
    assert metrics.pd > 0.05
    assert metrics.interception_ratio == pytest.approx(1.0)


def test_pure_randomness_still_beats_the_index_on_this_scenario():
    """Clarkson & Pollington, in measurement rather than in a citation.

    One emitter, one band at a time, and parameters the receiver has no prior knowledge of. This is
    exactly the regime their theorem covers, and the index does not beat random in it. Its coverage
    deadlines give its visit pattern a residual regularity that correlates with the emitter period;
    a uniform random schedule has none to correlate.

    The index's advantage lies in spectra with several emitters and exploitable structure, which is
    what scenarios A through D measure. The honest claim here is narrower: the floor is what keeps
    the index out of the lockout, and the lockout is what the sweep cannot escape at all.
    """
    floor = build_agent("ctmc", TRAP["bands"], rng=np.random.default_rng(3))
    assert _run(floor).pd > _run(IndexAgent.from_scenario(TRAP)).pd


def test_the_outcome_turns_on_whether_periodicity_locks_on_early():
    """The mechanism behind the spread, traced rather than guessed at.

    Detection on this scenario ranges from 0.08 to 1.00 across deadline settings, and the reason is
    not the schedule's own period. It is whether the first handful of detections arrive close
    enough together for the periodicity estimator to fit a period at all. At a 133 ms deadline it
    locks on by step 43 and then intercepts all 100 activations; at 160 ms it collects thirteen
    scattered detections in 800 steps and never fits one.

    That is a direct, measured argument for the Ai-ml-2 upgrade in solution spec Section 3.2. The
    training stand-in fits a median inter-arrival over detections alone and needs four of them with
    consistent gaps. The specified estimator evaluates a likelihood over hits *and misses*, which
    fits from far sparser evidence -- exactly the regime this scenario produces.
    """
    receiver = TRAP["receiver"]
    cycle = TRAP["bands"] * (receiver["step_ms"] + receiver["tuning_delay_ms"]) / 1000.0
    scores = {
        budget: _run(IndexAgent.from_scenario(TRAP, deadline_s=cycle / budget)).pd
        for budget in (0.6, 0.5, 0.4, 0.3)
    }
    assert all(pd > 0.0 for pd in scores.values()), "no deadline may reproduce the lockout"
    assert max(scores.values()) > 4 * min(scores.values()), "the bootstrapping threshold is real"


def test_dithering_the_trigger_narrows_the_spread_without_closing_it():
    """The synchronisation guard helps here and is not the whole answer, which is worth recording.

    A fixed trigger gives the visit pattern a period of its own, so dithering it is right on its own
    terms and does reduce the spread. It cannot close it, because the dominant factor is the
    estimator's bootstrapping threshold rather than the schedule's periodicity. Claiming the guard
    as the fix for this scenario would be claiming the wrong mechanism.
    """
    receiver = TRAP["receiver"]
    cycle = TRAP["bands"] * (receiver["step_ms"] + receiver["tuning_delay_ms"]) / 1000.0

    def spread(dither: float) -> float:
        scores = [
            _run(
                IndexAgent.from_scenario(
                    TRAP, deadline_s=cycle / budget, trigger_dither=dither
                )
            ).pd
            for budget in (0.6, 0.5, 0.4, 0.3)
        ]
        return max(scores) / max(min(scores), 1e-9)

    assert spread(0.25) < spread(0.0)
    assert spread(0.25) > 2.0


def test_the_lockout_does_not_depend_on_the_seed():
    """A sweep locked out at one seed is locked out at all of them: it is arithmetic, not luck."""
    for seed in (7, 11, 23, 101):
        sweep = build_agent("baseline", TRAP["bands"], {"stride": 1, "mode": "round_robin"})
        assert _run(sweep, seed=seed).pd == pytest.approx(0.0, abs=1e-9)
