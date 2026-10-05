"""Round-2 Bandit gate (docs/superpowers/specs/2026-10-05-efficiency-round2-gate.md). Same bootstrap as round 1 (effstats: 4000 resamples, 95%, seed 20261003).

  python r2_gate.py --dirs out_v1 --ref bandit --cand r2a_k12            # prints the checks and a verdict (exit 1 on FAIL)
"""
import argparse
import effstats as es
import select_rule as sr

SHORT, ALL_H = (80, 160), (80, 160, 400, 0)
DEMO = (80, 160, 400)


def gate(D, cand, ref, verbose=True):
    ok = {}
    out = []
    P = out.append
    # G1 / G1b
    rows = []
    g1 = True; g1b = True
    for h in SHORT:
        r = es.mean_ratio(D, cand, ref, h, "eff"); b = es.cell_ratio(D, cand, ref, "B", h)
        g1 &= r[1] >= 1.20; g1b &= b[1] >= 1.20
        rows.append(f"| {h} | {r[0]:.3f} [{r[1]:.3f}, {r[2]:.3f}] | {'PASS' if r[1] >= 1.20 else 'FAIL'} | {b[0]:.3f} [{b[1]:.3f}, {b[2]:.3f}] | {'PASS' if b[1] >= 1.20 else 'FAIL'} |")
    P("#### G1 / G1b efficiency at the live horizons (mean of ratios over A-G; Scenario B alone)\n")
    P("| horizon | mean ratio [95%] | G1 | Scenario B ratio [95%] | G1b |"); P("|---|---|---|---|---|"); out.extend(rows)
    # G2
    g2 = True
    P("\n#### G2 no loss on longer runs (lower end >= 1.00 at 400, >= 0.97 at full)\n"); P("| horizon | ratio [95%] | pass |"); P("|---|---|---|")
    for h, thr in ((400, 1.00), (0, 0.97)):
        r = es.mean_ratio(D, cand, ref, h, "eff"); p = r[1] >= thr; g2 &= p
        P(f"| {'full' if h == 0 else h} | {r[0]:.3f} [{r[1]:.3f}, {r[2]:.3f}] | {'PASS' if p else 'FAIL'} (>= {thr:.2f}) |")
    # G3
    g3 = True
    P("\n#### G3 detection (mean new - today, pp; lower end: Pd >= -1.0, HPDR >= -2.0)\n"); P("| metric | horizon | diff [95%] | pass |"); P("|---|---|---|---|")
    for m, thr in (("pd", -1.0), ("hpdr", -2.0)):
        for h in ALL_H:
            d = es.mean_diff(D, cand, ref, h, m); p = d[1] >= thr; g3 &= p
            P(f"| {m} | {'full' if h == 0 else h} | {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}] | {'PASS' if p else 'FAIL'} |")
    # G4
    g4 = True
    P("\n#### G4 per-scenario efficiency ratio (point [95%]); upper end >= 0.95 in every cell\n"); P("| horizon | " + " | ".join(es.SCEN) + " | pass |"); P("|---|" + "---|" * 8)
    for h in DEMO:
        cells, okh = [], True
        for s in es.SCEN:
            r = es.cell_ratio(D, cand, ref, s, h); okh &= r[2] >= 0.95
            cells.append(f"{r[0]:.2f} [{r[1]:.2f},{r[2]:.2f}]")
        g4 &= okh
        P(f"| {h} | " + " | ".join(cells) + f" | {'PASS' if okh else 'FAIL'} |")
    # G5
    g5 = True
    P("\n#### G5 coverage: distinct bursts, mean new - today (lower end >= -3.0 pp) and per scenario (upper end must not be below -10 pp)\n"); P("| horizon | mean diff [95%] | mean ok | worst scenario upper end | per-scenario ok |"); P("|---|---|---|---|---|")
    for h in ALL_H:
        d = es.mean_diff(D, cand, ref, h, "bursts"); cells = [es.cell_diff(D, cand, ref, s, h, "bursts") for s in es.SCEN]
        worst = min(c[2] for c in cells); pm, ps = d[1] >= -3.0, worst >= -10.0; g5 &= pm and ps
        P(f"| {'full' if h == 0 else h} | {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}] | {'PASS' if pm else 'FAIL'} | {worst:+.1f} | {'PASS' if ps else 'FAIL'} |")
    res = {"G1": g1, "G1b": g1b, "G2": g2, "G3": g3, "G4": g4, "G5": g5}
    P("\nVERDICT " + cand + ": " + ("PASS" if all(res.values()) else "FAIL") + "   " + "  ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in res.items()))
    if verbose:
        print("\n".join(out))
    return all(res.values()), res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True); ap.add_argument("--ref", default="bandit"); ap.add_argument("--cand", required=True)
    ap.add_argument("--base", default="out_base")
    a = ap.parse_args()
    D = {}
    for d in a.dirs:
        D.update(es.load_dir(d))
    ok, _ = gate(D, a.cand, a.ref)
    raise SystemExit(0 if ok else 1)
