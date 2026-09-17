"""Per-(simulation_id, band_id) detection-timestamp ring buffers (Ai-ml-2 Level 2).

The Backend posts one timestamp per confirmed detection. We keep a bounded, ordered history per
band and nothing else -- no simulation state, no emitter identities, no ground truth.

Concurrency: NFR-004 asks for at least 5 concurrent simulations at 64+ bands each, and uvicorn
serves these endpoints from a thread pool, so every mutation is under a lock. The lock is held
only for the list operation itself; the estimator runs on a *copy* taken under the lock, so a
slow fit never blocks an incoming update.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class BufferKey:
    simulation_id: str
    band_id: int


class DetectionBuffer:
    """Bounded history of ACTIVATION START times for one band of one simulation.

    THE BUFFER STORES ACTIVATIONS, NOT RAW DETECTIONS, and that distinction is the whole point.

    A receiver dwelling on an active band reports the same burst on every step it stays there.
    An earlier version kept the most recent N raw detections and clustered them only when
    fitting, which quietly destroyed the data: a scheduler camping on one band filled all N slots
    with consecutive steps of a single burst, evicted every earlier burst, and left the estimator
    with one activation and nothing to measure a period against. Measured on a real run, 557
    detections on one band collapsed to a single activation and no band in the whole simulation
    ever produced a periodicity claim.

    A burst is a *contiguous* run, so the test is against the previous detection, not against the
    burst's start. Measuring from the start instead splits a long dwell into a fresh activation
    every ``activation_gap`` steps, which fabricates a period equal to the gap - an artefact of
    the buffer rather than anything the emitter did. Only a real silence longer than
    ``activation_gap`` starts a new activation.

    The capacity then means "remember the last N bursts", which is what a period estimator needs.
    """

    __slots__ = ("_timestamps", "_capacity", "_gap", "_total_seen", "_last_raw")

    def __init__(self, capacity: int, activation_gap: float = 3.0) -> None:
        self._timestamps: list[float] = []
        self._capacity = int(capacity)
        self._gap = float(activation_gap)
        self._total_seen = 0
        self._last_raw: float | None = None

    def append(self, timestamp: float) -> bool:
        """Record a detection. Returns False when it continued a burst already recorded.

        Out-of-order arrivals are inserted in position rather than rejected: the Backend may
        batch or retry, and a timestamp that arrives late is still evidence about the emitter.
        """
        import bisect

        t = float(timestamp)
        buf = self._timestamps
        self._total_seen += 1

        # The common case: detections arrive in order, and this one continues the burst in
        # progress. Tracked against the last raw detection so an arbitrarily long dwell stays
        # one activation.
        if self._last_raw is not None and 0 <= t - self._last_raw <= self._gap:
            self._last_raw = t
            return False
        if self._last_raw is None or t > self._last_raw:
            self._last_raw = t

        i = bisect.bisect_left(buf, t)
        if i > 0 and t - buf[i - 1] <= self._gap:
            return False
        if i < len(buf) and buf[i] - t <= self._gap:
            return False

        buf.insert(i, t)
        if len(buf) > self._capacity:
            del buf[0 : len(buf) - self._capacity]
        return True

    @property
    def timestamps(self) -> list[float]:
        return list(self._timestamps)

    @property
    def total_seen(self) -> int:
        """Raw detections ever offered, including those absorbed into an existing burst."""
        return self._total_seen

    def __len__(self) -> int:
        return len(self._timestamps)


class BufferStore:
    """Thread-safe collection of per-(simulation_id, band_id) buffers."""

    def __init__(self, capacity: int = 64, max_tracked: int = 4096,
                 activation_gap: float = 3.0) -> None:
        self.capacity = capacity
        self.max_tracked = max_tracked
        self.activation_gap = activation_gap
        self._buffers: OrderedDict[tuple[str, int], DetectionBuffer] = OrderedDict()
        self._lock = threading.Lock()

    def record(self, simulation_id: str, band_id: int, timestamp: float) -> bool:
        key = (simulation_id, int(band_id))
        with self._lock:
            buf = self._buffers.get(key)
            if buf is None:
                buf = DetectionBuffer(self.capacity, self.activation_gap)
                self._buffers[key] = buf
            self._buffers.move_to_end(key)
            accepted = buf.append(timestamp)
            self._evict_locked()
            return accepted

    def snapshot(self, simulation_id: str, band_id: int) -> list[float]:
        """A copy of one band's history, so the estimator can fit without holding the lock."""
        with self._lock:
            buf = self._buffers.get((simulation_id, int(band_id)))
            return buf.timestamps if buf else []

    def stats(self, simulation_id: str, band_id: int) -> dict:
        with self._lock:
            buf = self._buffers.get((simulation_id, int(band_id)))
            if buf is None:
                return {"retained": 0, "total_seen": 0, "capacity": self.capacity}
            return {
                "retained": len(buf),
                "total_seen": buf.total_seen,
                "capacity": self.capacity,
            }

    def reset(self, simulation_id: str) -> int:
        """Clear every band of one simulation. Called on simulation reset."""
        with self._lock:
            keys = [k for k in self._buffers if k[0] == simulation_id]
            for k in keys:
                del self._buffers[k]
            return len(keys)

    def bands(self, simulation_id: str) -> list[int]:
        with self._lock:
            return sorted(k[1] for k in self._buffers if k[0] == simulation_id)

    def tracked(self) -> int:
        with self._lock:
            return len(self._buffers)

    def _evict_locked(self) -> None:
        while len(self._buffers) > self.max_tracked:
            self._buffers.popitem(last=False)
