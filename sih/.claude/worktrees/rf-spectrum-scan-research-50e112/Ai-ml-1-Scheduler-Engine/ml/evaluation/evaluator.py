"""Metrics engine -- every formula in PRD Section 12.

    Pd        = TP / (TP + FN)                     primary
    Pfa       = FP / (FP + TN)                     primary
    AIT       = mean(t_detect - t_active_start)    primary
    Latency   = per-event t_detect - t_active_start
    HPDR      = TP_hi / (TP + FN)_hi               primary
    IR        = unique emitters detected / present
    SE        = useful scans / total scans
    R_total   = sum r(t)
    Precision = TP / (TP + FP)
    Recall    = TP / (TP + FN)   (= Pd)
    F1        = 2PR / (P + R)
    Coverage  = distinct bands scanned / N
    MissRate  = FN / (TP + FN)  (= 1 - Pd)

TWO COUNTING RULES, both deliberate, both load-bearing for an honest comparison:

1. **Pd counts every band at every step.** A band that was active and never looked at is a
   false negative. If FN only counted scanned bands, a scanner that visited one band forever
   would report a perfect Pd -- which is exactly the failure mode the project is about.

2. **Pfa counts scanned bands only.** An unscanned band cannot raise a false alarm, so it
   contributes to neither FP nor TN. Counting idle unscanned bands as true negatives would
   drive Pfa toward zero for every policy and make the metric useless.

AIT averages over activation runs that were *eventually detected*, per the Section 12 formula
(the sum runs over detections). Runs never detected are captured by Pd and MissRate instead --
folding them into AIT as an infinite latency would make the average meaningless.

BUT THAT MAKES RAW AIT A TRAP FOR COMPARING TWO POLICIES, and it is worth being explicit about
because the trap is easy to fall into and hard to spot. Because the average is conditioned on
detection succeeding, a policy that intercepts *more* activation runs will usually report a
*worse* AIT -- the extra runs it catches are the hard, late ones the weaker policy missed
entirely, and they drag the mean up. Read alone, raw AIT would rank the better policy lower.

So ``ait_censored`` is reported alongside it: undetected runs are charged the full episode
length instead of being dropped. That is the standard right-censoring fix, it is defined over
*every* activation run rather than a detection-selected subset, and it is what the PRD
Definition-of-Done item 8 comparison should be read against. Use raw ``ait`` to describe how fast
a policy reacts when it does intercept; use ``ait_censored`` to compare two policies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np

from ml.environments.spectrum import GroundTruth


@dataclass
class EpisodeMetrics:
    """One episode's scoring. Field names are what the Backend surfaces via /internal/models."""

    # Primary (PRD Section 12)
    pd: float = 0.0
    pfa: float = 0.0
    ait: float = 0.0
    ait_censored: float = 0.0
    hpdr: float = 0.0
    mean_latency: float = 0.0
    median_latency: float = 0.0

    # Secondary
    interception_ratio: float = 0.0
    scan_efficiency: float = 0.0
    cumulative_reward: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    coverage: float = 0.0
    miss_rate: float = 0.0

    # Raw counts, kept so results can be re-aggregated or audited by hand
    tp: int = 0
    fn: int = 0
    fp: int = 0
    tn: int = 0
    tp_high_priority: int = 0
    fn_high_priority: int = 0
    steps: int = 0
    total_scans: int = 0
    useful_scans: int = 0
    invalid_steps: int = 0
    retunes: int = 0
    detected_runs: int = 0
    total_runs: int = 0
    latencies: list[int] = field(default_factory=list)

    def as_dict(self, include_latencies: bool = False) -> dict[str, Any]:
        d = asdict(self)
        if not include_latencies:
            d.pop("latencies", None)
        return d


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def score_episode(
    history: Sequence[dict], ground_truth: GroundTruth, num_bands: int
) -> EpisodeMetrics:
    """Score one episode from EWEnvironment.history plus the episode's ground truth."""
    m = EpisodeMetrics()
    m.steps = len(history)

    bands_scanned: set[int] = set()
    detected_emitters: set[int] = set()
    high_priority = ground_truth.priority > 1.0

    # Latency is per activation *run*, not per step, so a 30-step burst detected once counts as
    # one intercepted run rather than thirty.
    detected_runs: dict[tuple[int, int], int] = {}

    for record in history:
        t = record["t"]
        m.cumulative_reward += record["reward"]
        if not record["valid"]:
            m.invalid_steps += 1
        if record["retuned"]:
            m.retunes += 1

        for band, outcome in record["outcomes"].items():
            m.total_scans += 1
            bands_scanned.add(int(band))
            if outcome == "TP":
                m.tp += 1
                m.useful_scans += 1
                if high_priority[t, band]:
                    m.tp_high_priority += 1
                run_start = int(ground_truth.activation_starts[t, band])
                key = (int(band), run_start)
                if run_start >= 0 and key not in detected_runs:
                    detected_runs[key] = int(t - run_start)
            elif outcome == "FN":
                m.fn += 1
                m.useful_scans += 1  # the band was active: the scan was well aimed, just noisy
                if high_priority[t, band]:
                    m.fn_high_priority += 1
            elif outcome == "FP":
                m.fp += 1
            elif outcome == "TN":
                m.tn += 1

        for band in record["unscanned_misses"]:
            m.fn += 1
            if high_priority[t, band]:
                m.fn_high_priority += 1

        detected_emitters |= record["detected_emitters"]

    m.latencies = sorted(detected_runs.values())
    m.detected_runs = len(detected_runs)
    m.total_runs = _count_activation_runs(ground_truth)

    m.pd = _safe_div(m.tp, m.tp + m.fn)
    m.pfa = _safe_div(m.fp, m.fp + m.tn)
    m.hpdr = _safe_div(m.tp_high_priority, m.tp_high_priority + m.fn_high_priority)
    m.ait = float(np.mean(m.latencies)) if m.latencies else 0.0
    m.mean_latency = m.ait
    m.median_latency = float(np.median(m.latencies)) if m.latencies else 0.0
    # Right-censored: every undetected run is charged the full episode length, so the average
    # covers all activation runs rather than only the ones this policy happened to catch.
    m.ait_censored = _censored_ait(m.latencies, m.total_runs, m.steps)

    present = ground_truth.emitters_present
    m.interception_ratio = _safe_div(len(detected_emitters & present), len(present))
    m.scan_efficiency = _safe_div(m.useful_scans, m.total_scans)
    m.precision = _safe_div(m.tp, m.tp + m.fp)
    m.recall = m.pd
    m.f1 = _safe_div(2 * m.precision * m.recall, m.precision + m.recall)
    m.coverage = _safe_div(len(bands_scanned), num_bands)
    m.miss_rate = 1.0 - m.pd
    return m


def _censored_ait(latencies: Sequence[int], total_runs: int, horizon: int) -> float:
    if total_runs <= 0:
        return 0.0
    undetected = max(0, total_runs - len(latencies))
    return float((sum(latencies) + undetected * horizon) / total_runs)


def _count_activation_runs(ground_truth: GroundTruth) -> int:
    total = 0
    for b in range(ground_truth.num_bands):
        col = ground_truth.occupancy[:, b]
        starts = ground_truth.activation_starts[:, b][col]
        total += int(np.unique(starts).size)
    return total


def aggregate(episodes: Iterable[EpisodeMetrics]) -> dict[str, Any]:
    """Aggregate across episodes.

    Rates are recomputed from pooled counts rather than averaged, because averaging ratios across
    episodes of differing activity silently weights quiet episodes as heavily as busy ones.
    Latency-derived figures pool the raw per-run latencies for the same reason.
    """
    eps = list(episodes)
    if not eps:
        return {}

    tp = sum(e.tp for e in eps)
    fn = sum(e.fn for e in eps)
    fp = sum(e.fp for e in eps)
    tn = sum(e.tn for e in eps)
    tp_hi = sum(e.tp_high_priority for e in eps)
    fn_hi = sum(e.fn_high_priority for e in eps)
    useful = sum(e.useful_scans for e in eps)
    scans = sum(e.total_scans for e in eps)
    latencies = [x for e in eps for x in e.latencies]
    total_runs = sum(e.total_runs for e in eps)
    censored_sum = sum(
        sum(e.latencies) + (e.total_runs - len(e.latencies)) * e.steps for e in eps
    )

    pd = _safe_div(tp, tp + fn)
    precision = _safe_div(tp, tp + fp)
    rewards = [e.cumulative_reward for e in eps]

    return {
        "episodes": len(eps),
        "pd": pd,
        "pfa": _safe_div(fp, fp + tn),
        "ait": float(np.mean(latencies)) if latencies else 0.0,
        "ait_censored": _safe_div(censored_sum, total_runs),
        "median_latency": float(np.median(latencies)) if latencies else 0.0,
        "hpdr": _safe_div(tp_hi, tp_hi + fn_hi),
        "interception_ratio": float(np.mean([e.interception_ratio for e in eps])),
        "scan_efficiency": _safe_div(useful, scans),
        "precision": precision,
        "recall": pd,
        "f1": _safe_div(2 * precision * pd, precision + pd),
        "coverage": float(np.mean([e.coverage for e in eps])),
        "miss_rate": 1.0 - pd,
        "cumulative_reward_mean": float(np.mean(rewards)),
        "cumulative_reward_std": float(np.std(rewards)),
        "detected_runs": sum(e.detected_runs for e in eps),
        "total_runs": total_runs,
        "run_intercept_rate": _safe_div(sum(e.detected_runs for e in eps), total_runs),
        "invalid_steps": sum(e.invalid_steps for e in eps),
        "retunes": sum(e.retunes for e in eps),
        "counts": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
    }
