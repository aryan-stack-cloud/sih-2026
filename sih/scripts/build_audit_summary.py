"""Build a measured A–G scorecard from run_audit_sweep.ps1 result files.

Usage: python scripts/build_audit_summary.py audit-results output.md [model-manifest.json]
The input files are the Backend experiment API's ``data`` objects, one per scenario.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCENARIOS = "ABCDEFG"
POLICIES = ("baseline", "random", "ctmc", "index", "bandit", "q_learning", "dqn", "ppo")


def percentage(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def main(input_dir: Path, output_file: Path, manifest_file: Path | None = None) -> None:
    results = {}
    for scenario in SCENARIOS:
        source = input_dir / f"results_{scenario}.json"
        if not source.exists():
            raise SystemExit(f"Missing {source}; the sweep is incomplete")
        raw = json.loads(source.read_text(encoding="utf-8-sig"))
        result = raw.get("data", raw)
        if result.get("scenario") != scenario or set(result.get("policies", {})) != set(POLICIES):
            raise SystemExit(f"Incomplete or mismatched scenario result: {source}")
        results[scenario] = result

    lines = [
        "---",
        "kind: spec",
        'title: "Full A–G policy scorecard"',
        "---",
        "",
        "# Full A–G policy scorecard",
        "",
        "Backend experiment results for all eight policies on each scenario. Each scenario uses",
        "the same seeds across policies. Pd and HPDR count active band moments; run interception",
        "counts distinct activation runs caught at least once. Censored AIT includes missed",
        "runs, so lower is better. These are synthetic simulation results, not field measurements.",
        "Ten seeds per scenario are below the project's 20-episode stability recommendation and",
        "do not establish statistical significance for small differences.",
        "",
    ]

    lines.extend([
        "## Comparisons against the fixed sweep",
        "",
        "Count of scenarios where the policy's aggregate metric is better than the same-seed fixed sweep.",
        "A tie is not counted. Lower censored AIT is better; higher is better for the other metrics.",
        "",
        "| Policy | Pd | Efficiency | HPDR | Runs caught | Censored AIT |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for policy in POLICIES[1:]:
        def wins(metric: str, lower: bool = False) -> int:
            return sum(
                (results[s]["policies"][policy][metric]
                 < results[s]["policies"]["baseline"][metric]) if lower else
                (results[s]["policies"][policy][metric]
                 > results[s]["policies"]["baseline"][metric])
                for s in SCENARIOS
            )
        lines.append(
            f"| {policy} | {wins('pd')}/7 | {wins('scan_efficiency')}/7 "
            f"| {wins('hpdr')}/7 | {wins('run_intercept_rate')}/7 "
            f"| {wins('ait_censored', lower=True)}/7 |"
        )
    lines.append("")

    for scenario, result in results.items():
        seeds = result.get("seeds", [])
        lines.extend([
            f"## Scenario {scenario}: {result.get('scenario_name', scenario)}",
            "",
            f"{result['episodes']} episodes × {result['duration_steps']} steps; "
            f"seeds {seeds[0]}–{seeds[-1]}.",
            "",
            "| Policy | Pd | Efficiency | HPDR | Run interception | Censored AIT | Fallback decisions | Serving model |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ])
        metrics = result["policies"]
        for policy in POLICIES:
            m = metrics[policy]
            model_ids = ", ".join(m.get("model_ids") or []) or "—"
            lines.append(
                f"| {policy} | {percentage(m.get('pd'))} | {percentage(m.get('scan_efficiency'))} "
                f"| {percentage(m.get('hpdr'))} | {percentage(m.get('run_intercept_rate'))} "
                f"| {m.get('ait_censored', float('nan')):.1f} "
                f"| {m.get('fallback_decisions', 0)} | {model_ids} |"
            )
        lines.append("")

        best_pd = max(POLICIES, key=lambda p: metrics[p].get("pd") or -1)
        best_eff = max(POLICIES, key=lambda p: metrics[p].get("scan_efficiency") or -1)
        best_ait = min(POLICIES, key=lambda p: metrics[p].get("ait_censored", float("inf")))
        best_runs = max(POLICIES, key=lambda p: metrics[p].get("run_intercept_rate") or -1)
        baseline = metrics["baseline"]
        lines.append(
            f"Highest Pd: **{best_pd} ({percentage(metrics[best_pd]['pd'])})**; "
            f"highest efficiency: **{best_eff} ({percentage(metrics[best_eff]['scan_efficiency'])})**. "
            f"Fixed sweep: {percentage(baseline['pd'])} Pd and "
            f"{percentage(baseline['scan_efficiency'])} efficiency."
        )
        lines.append(
            f"Fastest censored interception: **{best_ait} "
            f"({metrics[best_ait]['ait_censored']:.1f} steps)**; "
            f"highest distinct-run interception: **{best_runs} "
            f"({percentage(metrics[best_runs]['run_intercept_rate'])})**."
        )
        lines.append("")

    fallbacks = [
        (scenario, policy, results[scenario]["policies"][policy].get("fallback_decisions", 0))
        for scenario in SCENARIOS for policy in POLICIES[2:]
        if results[scenario]["policies"][policy].get("fallback_decisions", 0) > 0
    ]
    lines.extend(["## Serving integrity", ""])
    if fallbacks:
        lines.append("The following model runs partially used the local sweep and need separate interpretation:")
        lines.append("")
        lines.extend(f"- Scenario {s}, {p}: {n} fallback decisions" for s, p, n in fallbacks)
    else:
        lines.append("All 42 model-policy × scenario groups report zero fallback decisions.")
    if manifest_file is not None:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
        expected = {(row["scenario"], row["algorithm"]): row["model_id"] for row in manifest}
        mismatches = [
            (scenario, policy, results[scenario]["policies"][policy].get("model_ids"),
             expected.get((scenario, policy)))
            for scenario in SCENARIOS for policy in POLICIES[2:]
            if results[scenario]["policies"][policy].get("model_ids")
            != [expected.get((scenario, policy))]
        ]
        lines.append(
            f"{42 - len(mismatches)}/42 groups report the expected scenario-specific checkpoint ID."
        )
        if mismatches:
            lines.extend(
                f"- Scenario {scenario}, {policy}: served {served}; expected {want}"
                for scenario, policy, served, want in mismatches
            )
    lines.append("")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output_file}")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        raise SystemExit("Usage: build_audit_summary.py <results-dir> <output.md> [model-manifest.json]")
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) == 4 else None)
