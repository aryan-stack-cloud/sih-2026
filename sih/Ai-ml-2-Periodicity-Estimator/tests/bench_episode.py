"""Reproduce the Backend's two-scan update/predict loop in process.

Run from the service root: python tests/bench_episode.py --bands 16 32
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from periodicity.service import PeriodicityService  # noqa: E402


def episode(bands: int, steps: int = 2000) -> float:
    service = PeriodicityService()
    rng = random.Random(20260925)
    ids = list(range(bands))
    started = perf_counter()
    for t in range(steps):
        for band in ((2 * t) % bands, (2 * t + 1) % bands):
            if band % 4 < 2:
                period = 20 + (band % 5) * 7
                detected = (t - band * 3) % period < max(2, round(period * 0.12))
            else:
                detected = rng.random() < 0.10
            if detected:
                service.update("episode", band, float(t))
            else:
                service.observe_miss("episode", band, float(t))
        service.predict_many("episode", ids, float(t + 1))
    return (perf_counter() - started) * 1000 / steps


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bands", nargs="+", type=int, default=[16, 32])
    parser.add_argument("--steps", type=int, default=2000)
    args = parser.parse_args()
    for bands in args.bands:
        per_step = episode(bands, args.steps)
        print(f"{bands} bands, {args.steps} steps: {per_step:.3f} ms/step; "
              f"total {per_step * args.steps / 1000:.3f} s", flush=True)
