"""Report all Q tuning variants and training replicates; no validation/reserve use."""
import json
import effstats as es
import select_rule as sr

D = sr.load(['out_s4', 'out_r2q1', 'out_r2q2', 'out_r2qr'])
labels = sorted(l for l in es.labels(D) if l.startswith('r2q'))
result = {}
for s in 'BF':
    print(f'\nScenario {s}, efficiency %, tuning seeds 20000-20019')
    print('| arm | 80 | 160 | original ratios 80/160 |')
    print('|---|---|---|---|')
    result[s] = {}
    for label in ['q', 'q4_e4c2'] + labels:
        if not all((s,h,label) in D for h in (80,160)): continue
        eff = [100*es.point(D[s,h,label], 'eff') for h in (80,160)]
        ratio = [es.cell_ratio(D,label,'q',s,h) for h in (80,160)]
        result[s][label] = {'eff': eff, 'ratio_original': ratio}
        print(f'| {label} | {eff[0]:.2f} | {eff[1]:.2f} | {ratio[0][0]:.3f} / {ratio[1][0]:.3f} |')
    eligible = {label:v for label,v in result[s].items() if label.startswith('r2q')}
    best = max(eligible, key=lambda label:min(r[0] for r in eligible[label]['ratio_original']))
    print(f'Best minimum point ratio: {best}, {min(r[0] for r in eligible[best]["ratio_original"]):.3f}')
(sr.HERE/'q_round2_tuning_summary.json').write_text(json.dumps(result,indent=2))
