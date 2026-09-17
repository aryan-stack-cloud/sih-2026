"""The synchronisation trap: the failure open loop cannot see in itself.

A receiver sweeping 8 bands one at a time visits band b whenever ``t mod 8 == b``. An emitter in
band 5 illuminating for one step every 8 at phase 3 is visible only when ``t mod 8 == 3``. Those
two sets never meet. The sweep runs flawlessly, reports a probability of detection of exactly
zero, and is indistinguishable from a receiver watching an empty band.

This is Kelly, Noone and Perkins' result made concrete, and Clarkson's own worked example has an
emitter invisible to a one-second sweep until the dwell in its band is raised past 400 ms. It is
not a contrived edge case: any fixed-period schedule has a family of emitter periods it can never
see, and no amount of extra observation time helps.

Run it:

    python scripts/sync_trap_demo.py
    python scripts/sync_trap_demo.py --seeds 7,11,23,101 --steps 800

What the three rows show:

* **round-robin** never intercepts the emitter. Not late, not rarely: never.
* **randomised floor** intercepts about one activation in eight, which is what an uninformed
  random search buys and is exactly Clarkson & Pollington's bound.
* **index (SCT)** finds the emitter through the floor at a cold start, learns its period, and then
  dwells on it at the right phase, intercepting every activation at zero latency.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from ml.agents.factory import build_agent  # noqa: E402
from ml.agents.index_agent import IndexAgent  # noqa: E402
from ml.environments.environment import make_env  # noqa: E402
from ml.evaluation.runner import run_episode  # noqa: E402

TRAP = {
    "scenario_id": "B",
    "name": "Synchronisation trap",
    "bands": 8,
    "emitters": 1,
    "duration_steps": 800,
    "seed": 7,
    "emitter_mix": {"periodic": 1.0},
    "high_priority_fraction": 1.0,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="7,11,23,101")
    parser.add_argument("--steps", type=int, default=800)
    args = parser.parse_args()

    scenario = dict(TRAP, duration_steps=args.steps)
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]

    policies = [
        (
            "round-robin sweep",
            lambda: build_agent(
                "baseline", scenario["bands"], {"stride": 1, "mode": "round_robin"}
            ),
        ),
        (
            "randomised floor",
            lambda: build_agent("ctmc", scenario["bands"], rng=np.random.default_rng(3)),
        ),
        ("index (SCT)", lambda: IndexAgent.from_scenario(scenario)),
    ]

    print(
        f"\n  8 bands, one band at a time. Emitter in band 5, scan period 8 steps,"
        f"\n  illuminating one step in eight at phase 3. {args.steps} steps,"
        f" seeds {seeds}.\n"
    )
    header = f"  {'policy':<20}{'Pd':>10}{'intercepted':>14}{'censored AIT':>16}"
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for label, make in policies:
        runs = []
        for seed in seeds:
            env = make_env(scenario, seed=seed)
            runs.append(run_episode(env, make(), seed=seed))
        pd = float(np.mean([m.pd for m in runs]))
        ratio = float(np.mean([m.interception_ratio for m in runs]))
        ait = float(np.mean([m.ait_censored for m in runs]))
        print(f"  {label:<20}{pd:>10.3f}{ratio:>14.3f}{ait:>16.1f}")

    print("-" * len(header))
    print(
        "\n  The sweep is not slow here, it is blind. No extra observation time helps, because\n"
        "  the two window functions are locked out of each other by arithmetic. Every fixed-period\n"
        "  schedule has a family of emitter periods it can never intercept, and it cannot tell\n"
        "  that family apart from an empty band.\n"
    )


if __name__ == "__main__":
    main()
