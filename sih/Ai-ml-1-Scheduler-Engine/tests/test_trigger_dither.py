"""Dithering the deadline trigger, so the schedule stops having a period of its own.

The trap scenario exposed this. The override fires at a fixed staleness, so the visit pattern it
produces is itself periodic, and against an 8-step emitter a 133 ms deadline aligned perfectly
while 160 ms aliased badly: the same policy scored 1.000 and 0.080 on detection with a 20% change
in one derived constant. A scheduler whose performance swings by a factor of twelve on an
arithmetic coincidence is not one you can reason about.

The fix is the same one the synchronisation guard prescribes for revisit intervals, applied to the
trigger instead: advance it by a golden-ratio Kronecker sequence indexed on the band's revisit
count. The dither only ever brings the trigger *earlier*, so the coverage guarantee is untouched,
and it is deterministic in the revisit count, so a run still replays exactly from its seed.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.scheduling.deadlines import RevisitDeadlines


def deadlines(n: int = 8, seconds: float = 0.300, **kwargs) -> RevisitDeadlines:
    return RevisitDeadlines(deadlines_s=np.full(n, seconds), slot_s=0.010, **kwargs)


# -- the trigger ---------------------------------------------------------------------------------

def test_zero_dither_reproduces_the_fixed_trigger():
    plain = deadlines(trigger_dither=0.0)
    assert plain.trigger(revisit_counts=np.arange(8)) == pytest.approx(plain.deadline_slots)


def test_the_trigger_never_exceeds_the_plain_deadline():
    """The dither only advances the trigger, so the guarantee is untouched."""
    dithered = deadlines(trigger_dither=0.25)
    for n in range(200):
        trigger = dithered.trigger(revisit_counts=np.full(8, n))
        assert np.all(trigger <= dithered.deadline_slots)


def test_the_trigger_varies_between_successive_revisits():
    """The whole point: consecutive revisits of one band must not fire at the same staleness."""
    dithered = deadlines(trigger_dither=0.25)
    seen = {int(dithered.trigger(revisit_counts=np.full(1, n))[0]) for n in range(40)}
    assert len(seen) > 3


def test_the_trigger_sequence_is_deterministic():
    a = deadlines(trigger_dither=0.25)
    b = deadlines(trigger_dither=0.25)
    counts = np.arange(8)
    assert a.trigger(revisit_counts=counts) == pytest.approx(b.trigger(revisit_counts=counts))


def test_the_trigger_stays_at_least_one_slot():
    tiny = deadlines(n=4, seconds=0.020, trigger_dither=0.9)  # 2 slots
    for n in range(50):
        assert np.all(tiny.trigger(revisit_counts=np.full(4, n), lookahead=99) >= 1)


def test_a_larger_dither_spreads_the_trigger_further():
    narrow = deadlines(trigger_dither=0.1)
    wide = deadlines(trigger_dither=0.5)
    spread = lambda d: len({int(d.trigger(revisit_counts=np.full(1, n))[0]) for n in range(60)})
    assert spread(wide) > spread(narrow)


def test_the_lookahead_and_the_dither_compose():
    d = deadlines(trigger_dither=0.25)
    with_lookahead = d.trigger(revisit_counts=np.full(8, 3), lookahead=7)
    without = d.trigger(revisit_counts=np.full(8, 3), lookahead=0)
    assert np.all(with_lookahead < without)


def test_a_negative_dither_is_rejected():
    with pytest.raises(ValueError):
        deadlines(trigger_dither=-0.1)


# -- overdue uses it ------------------------------------------------------------------------------

def test_overdue_fires_earlier_on_a_dithered_revisit():
    d = deadlines(trigger_dither=0.25)
    counts = np.full(8, 1)  # golden_phase(1) = 0.618, so the trigger is well advanced
    staleness = d.trigger(revisit_counts=counts)
    assert d.overdue(staleness, revisit_counts=counts) != []


def test_overdue_without_counts_behaves_as_before():
    """Callers that have not adopted the dither keep the old behaviour exactly."""
    d = deadlines(trigger_dither=0.25)
    assert d.overdue(np.full(8, 29)) == []
    assert len(d.overdue(np.full(8, 30))) == 8
