# B-only V3 validation: frozen draw4-B vs live-B (seeds 25000–25019, n=20)

Frozen SHA verified before the run. Paired bootstrap 4000/95%/seed 20261003.

| Check | Result | Bar | Verdict |
|---|---|---|---|
| B80 1.178 [1.088, 1.284] / B160 1.143 [1.039, 1.255] | lowers 1.088 / 1.039 | ≥ 1.15 | B1 FAIL |
| B400 1.174 [1.076, 1.281] / Bfull 1.057 [1.013, 1.105] | lowers clear | 1.00 / 0.97 | B2 PASS |
| Pd +2.4/+3.0/+4.3/+2.0 (lowers ≥ +0.6) | PASS | −1.0 | — |
| HPDR +4.2/+5.0/+1.4/−2.3 (full lower −8.11) | full fails | −2.0 | B3 FAIL |
| Bursts −3.0/−3.2/−3.6/−2.6 (lowers −5.0 to −5.8) | all fail | −3.0 | B4 FAIL |

**VERDICT: FAIL (B1/B3/B4). No C3 run — C3 (26000–26019) stays pristine. No sandbox,
no live steps.**

Reading: draw4's B-effect replicates in DIRECTION a third time (V2 1.173 → C2 1.255 →
V3 1.178 at 80 steps) but not at gate strength: points sit ~1.15–1.18 with lower ends
~1.04–1.09, and B-local distinct-burst losses (~−3 pp, lower ends past −5) are a real,
Dashboard-visible cost on the very scenario targeted. The effect is likely real but
smaller than the bar and bundled with a coverage cost — exactly what the gate was
built to catch. Per-world evidence: `C:\w\r3\b_V3_worlds.json`.
