"""Regressions for sampled-period ambiguity, cache lifetime, and concurrent fitting."""

from __future__ import annotations

import threading

import pytest

from periodicity.config import EstimatorConfig
from periodicity.buffers.detection_buffer import DetectionBuffer
from periodicity.estimator.periodicity_estimator import estimate_period_with_misses
from periodicity.service import PeriodicityService


def test_round_robin_revisit_does_not_become_emitter_period():
    # N=16, K=2 revisits this band every eight steps. A period-20, two-step
    # emitter is observationally aliased at this cadence; the safe answer is no claim.
    aliased = [(float(t), t % 20 < 2) for t in range(0, 2000, 8)]
    estimate = estimate_period_with_misses(aliased[-128:])
    assert not estimate.usable
    assert estimate.confidence == 0

    # An incommensurate emitter can be recovered from the same scan cadence.
    identifiable = [(float(t), t % 37 < 4) for t in range(0, 2000, 8)]
    estimate = estimate_period_with_misses(identifiable[-128:])
    assert estimate.period == pytest.approx(37, abs=0.5)
    assert estimate.confidence > 0.95


def test_round_robin_alias_matrix_has_no_wrong_period_claims():
    correct = 0
    for revisit in (8, 12, 16):
        for period in (17, 19, 20, 23, 24, 29, 37, 40, 53, 61):
            duty = max(2, round(period * 0.1))
            observations = [
                (float(t), t % period < duty)
                for t in range(0, 2000, revisit)
            ][-128:]
            estimate = estimate_period_with_misses(observations)
            if estimate.period is not None:
                assert abs(estimate.period - period) <= 1, (revisit, period, estimate)
                correct += 1
    assert correct >= 20


def test_batched_service_still_recovers_identifiable_alias_matrix():
    correct = 0
    for revisit in (8, 12, 16):
        for period in (17, 19, 20, 23, 24, 29, 37, 40, 53, 61):
            duty = max(2, round(period * 0.1))
            svc = PeriodicityService()
            for t in range(0, 2000, revisit):
                if t % period < duty:
                    svc.update("matrix", 0, float(t))
                else:
                    svc.observe_miss("matrix", 0, float(t))
            estimate = svc.estimate("matrix", 0)
            if estimate.period is not None:
                assert abs(estimate.period - period) <= 1, (revisit, period, estimate)
                correct += 1
    assert correct >= 20


def test_fit_cache_is_bounded_across_simulations_and_reset():
    svc = PeriodicityService(EstimatorConfig(max_tracked_bands=3))
    for i in range(12):
        svc.update(f"sim_{i}", 0, float(i * 10))
        svc.observe_miss(f"sim_{i}", 0, float(i * 10 + 1))
        svc.estimate(f"sim_{i}", 0)
    assert len(svc._fits) <= 3
    assert len(svc._fit_sources) <= 3
    assert len(svc._misses_since_fit) <= 3
    assert len(svc._hits_since_fit) <= 3
    assert len(svc.buffers._buffers) <= 3
    assert len(svc.buffers._misses) <= 3
    svc.reset("sim_11")
    assert ("sim_11", 0) not in svc._fits
    assert svc.buffers.snapshot("sim_11", 0) == []
    assert svc.buffers.snapshot_misses("sim_11", 0) == []


def test_reset_counts_and_clears_miss_only_bands():
    svc = PeriodicityService()
    svc.observe_miss("miss_only", 7, 12.0)
    assert svc.reset("miss_only") == 1
    assert svc.buffers.snapshot_misses("miss_only", 7) == []


def test_late_detection_retimes_or_joins_activation_starts():
    buf = DetectionBuffer(capacity=8, activation_gap=3)
    buf.append(10)
    buf.append(16)
    assert buf.append(13) is True
    assert buf.timestamps == [10]
    buf.append(30)
    assert buf.append(28) is True
    assert buf.timestamps == [10, 28]


def test_update_during_fit_cannot_restore_stale_cache(monkeypatch):
    from periodicity import service as module

    svc = PeriodicityService()
    for i in range(8):
        svc.update("race", 0, float(i * 20))
    svc._fits.clear()  # force a fit on the worker
    svc._fit_sources.clear()
    started = threading.Event()
    release = threading.Event()
    original = module.estimate_period
    calls = 0

    def delayed(timestamps, config):
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            assert release.wait(5)
        return original(timestamps, config)

    monkeypatch.setattr(module, "estimate_period", delayed)
    answers = []
    worker = threading.Thread(target=lambda: answers.append(svc.estimate("race", 0)))
    worker.start()
    assert started.wait(5)
    svc.update("race", 0, 160.0)
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert answers[0].samples == 9
    assert svc.estimate("race", 0).samples == 9


def test_reset_during_fit_cannot_restore_cleared_simulation(monkeypatch):
    from periodicity import service as module

    svc = PeriodicityService()
    for i in range(8):
        svc.update("race_reset", 0, float(i * 20))
    svc._fits.clear()
    svc._fit_sources.clear()
    started = threading.Event()
    release = threading.Event()
    original = module.estimate_period
    calls = 0

    def delayed(timestamps, config):
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            assert release.wait(5)
        return original(timestamps, config)

    monkeypatch.setattr(module, "estimate_period", delayed)
    answers = []
    worker = threading.Thread(target=lambda: answers.append(svc.estimate("race_reset", 0)))
    worker.start()
    assert started.wait(5)
    svc.reset("race_reset")
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert not answers[0].usable
    assert not svc.estimate("race_reset", 0).usable
