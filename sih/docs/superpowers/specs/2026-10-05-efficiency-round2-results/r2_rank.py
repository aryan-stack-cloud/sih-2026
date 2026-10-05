"""Round-2 Bandit selection on the TUNING seeds (point estimates). Usage: python r2_rank.py [--pool all|new] [--top N] [extra labels...]

Predicted-pass thresholds (what a candidate's T point estimate must reach so that its C2 interval would clear the gate with the noise seen in round 1):
  R80, R160 >= 1.25 ; Scenario B ratio at 80 and 160 >= 1.25 ; R400 >= 1.05 ; Rfull >= 1.014
  dPd >= 0.0 pp, dHPDR >= +0.7 pp, dBursts >= -1.5 pp at 80/160/400/full ; no scenario ratio at 80/160/400 below 0.95
Violation score = sum of normalised shortfalls (scale in the code). Finalists: lowest score, ties by min(R80, R160).
"""
import sys
import effstats as es
import select_rule as sr

DIRS = ["out_s1", "out_s1al", "out_s2", "out_s3", "out_s4", "out_s5", "out_s6", "out_deep_s2", "out_align", "out_r2s1", "out_r2s2", "out_r2s3"]
D = sr.load([d for d in DIRS if (sr.HERE / d).exists()])
ref = "bandit"
H = (80, 160, 400, 0)


def row(lab):
    R = {h: es.mean_ratio(D, lab, ref, h, "eff")[0] for h in H}
    B = {h: es.cell_ratio(D, lab, ref, "B", h)[0] for h in (80, 160)}
    cells = min(es.cell_ratio(D, lab, ref, s, h)[0] for s in es.SCEN for h in (80, 160, 400))
    g = {(m, h): es.mean_diff(D, lab, ref, h, m)[0] for m in ("pd", "hpdr", "bursts") for h in H}
    v = 0.0
    v += sum(max(0, 1.25 - R[h]) / 0.05 for h in (80, 160))
    v += sum(max(0, 1.25 - B[h]) / 0.05 for h in (80, 160))
    v += max(0, 1.05 - R[400]) / 0.03 + max(0, 1.014 - R[0]) / 0.02
    v += sum(max(0, 0.0 - g[("pd", h)]) / 0.5 for h in H)
    v += sum(max(0, 0.7 - g[("hpdr", h)]) / 1.0 for h in H)
    v += sum(max(0, -1.5 - g[("bursts", h)]) / 0.75 for h in H)
    v += max(0, 0.95 - cells) / 0.05
    return {"lab": lab, "R": R, "B": B, "cells": cells, "g": g, "viol": v, "obj": min(R[80], R[160])}


if __name__ == "__main__":
    args = sys.argv[1:]
    top = 14
    pool = "all"
    labs_extra = []
    i = 0
    while i < len(args):
        if args[i] == "--top": top = int(args[i + 1]); i += 2
        elif args[i] == "--pool": pool = args[i + 1]; i += 2
        else: labs_extra.append(args[i]); i += 1
    cand = [l for l in es.labels(D) if l.startswith("b") and not l.startswith("bandit") and l != "b6_e4c2_ep30" or l.startswith("r2a") or l.startswith("r2n") or l.startswith("r2m")]
    if pool == "new":
        cand = [l for l in cand if l.startswith("r2")]
    cand = sorted(set(cand) | set(labs_extra))
    rows = []
    for lab in cand:
        try:
            if sr.complete(D, lab, ref):
                rows.append(row(lab))
        except KeyError:
            pass
    rows.sort(key=lambda r: (round(r["viol"], 3), -r["obj"]))
    print("| candidate | viol | R80 | R160 | R400 | Rfull | B80 | B160 | worst cell | dPd 80/160/400/full | dHPDR | dBursts |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows[:top]:
        g = r["g"]
        f = lambda m: "/".join(f"{g[(m, h)]:+.1f}" for h in H)  # noqa: E731
        print(f"| `{r['lab']}` | {r['viol']:.1f} | {r['R'][80]:.2f} | {r['R'][160]:.2f} | {r['R'][400]:.2f} | {r['R'][0]:.2f} | {r['B'][80]:.2f} | {r['B'][160]:.2f} | {r['cells']:.2f} | {f('pd')} | {f('hpdr')} | {f('bursts')} |")
