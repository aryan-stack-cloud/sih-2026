"""Detection-timestamp buffers (Ai-ml-2 Level 2).

Level 2 DoD: the buffer accumulates and bounds timestamps correctly across concurrent
simulation IDs.
"""

from __future__ import annotations

import threading

import pytest

from periodicity.buffers.detection_buffer import BufferStore, DetectionBuffer


def test_buffer_keeps_timestamps_in_order():
    b = DetectionBuffer(capacity=10)
    for t in (30, 10, 20):
        b.append(t)
    assert b.timestamps == [10, 20, 30]


def test_out_of_order_arrivals_are_inserted_not_dropped():
    """The Backend may batch or retry; a late timestamp is still evidence."""
    b = DetectionBuffer(capacity=10)
    for t in (0, 20, 40):
        b.append(t)
    assert b.append(30) is True
    assert b.timestamps == [0, 20, 30, 40]


def test_duplicates_are_rejected():
    """Counting one activation twice would fabricate a zero-length inter-arrival."""
    b = DetectionBuffer(capacity=10)
    assert b.append(15) is True
    assert b.append(15) is False
    assert b.timestamps == [15]


def test_consecutive_detections_are_one_activation():
    """A receiver dwelling on a live band reports the same burst every step it stays."""
    b = DetectionBuffer(capacity=10, activation_gap=3.0)
    assert b.append(100) is True
    for t in (101, 102, 103):
        assert b.append(t) is False
    assert b.timestamps == [100]
    assert b.total_seen == 4


def test_a_separate_burst_takes_its_own_slot():
    b = DetectionBuffer(capacity=10, activation_gap=3.0)
    for t in (100, 101, 120, 121, 140):
        b.append(t)
    assert b.timestamps == [100, 120, 140]


def test_camping_does_not_evict_the_history_a_period_needs():
    """The bug this buffer exists to prevent.

    Storing raw detections meant a scheduler camping on one band filled every slot with
    consecutive steps of a single burst and evicted every earlier burst. Measured on a real run,
    557 detections on one band left exactly one activation and no band in the simulation ever
    produced a periodicity claim.
    """
    b = DetectionBuffer(capacity=16, activation_gap=3.0)
    for burst_start in range(0, 400, 20):
        for step in range(12):           # a long dwell on every visit
            b.append(burst_start + step)
    assert len(b) >= 8, "the period is unmeasurable if dwell evicts the burst history"
    gaps = [round(b.timestamps[i + 1] - b.timestamps[i]) for i in range(len(b) - 1)]
    assert set(gaps) == {20}


def test_buffer_is_bounded_and_drops_the_oldest():
    b = DetectionBuffer(capacity=5)
    for t in range(0, 200, 10):
        b.append(t)
    assert b.timestamps == [150, 160, 170, 180, 190]
    assert len(b) == 5


def test_total_seen_survives_eviction():
    b = DetectionBuffer(capacity=5)
    for t in range(0, 200, 10):
        b.append(t)
    assert b.total_seen == 20 and len(b) == 5


# -- the store ---------------------------------------------------------------------------------

def test_store_applies_the_activation_gap():
    store = BufferStore(capacity=16, activation_gap=3.0)
    for t in (10, 11, 12, 40, 41):
        store.record("sim_a", 0, t)
    assert store.snapshot("sim_a", 0) == [10.0, 40.0]


def test_bands_of_different_simulations_do_not_mix():
    store = BufferStore(capacity=16)
    store.record("sim_a", 3, 10)
    store.record("sim_b", 3, 99)
    assert store.snapshot("sim_a", 3) == [10]
    assert store.snapshot("sim_b", 3) == [99]


def test_bands_within_a_simulation_do_not_mix():
    store = BufferStore(capacity=16)
    store.record("sim_a", 1, 10)
    store.record("sim_a", 2, 20)
    assert store.snapshot("sim_a", 1) == [10]
    assert store.bands("sim_a") == [1, 2]


def test_snapshot_returns_a_copy():
    store = BufferStore(capacity=16)
    store.record("sim_a", 0, 5)
    snap = store.snapshot("sim_a", 0)
    snap.append(999)
    assert store.snapshot("sim_a", 0) == [5]


def test_reset_clears_only_the_named_simulation():
    store = BufferStore(capacity=16)
    for band in range(4):
        store.record("sim_a", band, 1)
    store.record("sim_b", 0, 1)

    assert store.reset("sim_a") == 4
    assert store.bands("sim_a") == []
    assert store.snapshot("sim_b", 0) == [1]


def test_unknown_band_reads_as_empty_rather_than_erroring():
    """The Backend asks for every band before every decision, including untouched ones."""
    store = BufferStore(capacity=16)
    assert store.snapshot("sim_missing", 7) == []
    assert store.stats("sim_missing", 7)["retained"] == 0


def test_tracked_pairs_are_capped():
    store = BufferStore(capacity=4, max_tracked=10)
    for band in range(50):
        store.record("sim_a", band, 1)
    assert store.tracked() == 10


def test_concurrent_writes_across_simulations_are_all_recorded():
    """NFR-004: >= 5 concurrent simulations, >= 64 bands each."""
    store = BufferStore(capacity=256, max_tracked=8192)
    sims = [f"sim_{i}" for i in range(5)]
    errors: list[BaseException] = []

    def writer(sim: str) -> None:
        try:
            for band in range(64):
                for t in range(10):
                    store.record(sim, band, t * 10)
        except BaseException as exc:  # pragma: no cover - surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(s,)) for s in sims]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert store.tracked() == 5 * 64
    for sim in sims:
        assert len(store.bands(sim)) == 64
        assert store.snapshot(sim, 0) == [t * 10 for t in range(10)]


def test_concurrent_writes_to_one_band_lose_nothing():
    """Five threads writing distinct, well-separated bursts must all be recorded."""
    store = BufferStore(capacity=4096)

    def writer(offset: int) -> None:
        for t in range(100):
            store.record("sim_x", 0, offset * 10 + t * 50)

    threads = [threading.Thread(target=writer, args=(o,)) for o in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(store.snapshot("sim_x", 0)) == 500
