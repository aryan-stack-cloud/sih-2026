"""Validate completion, pairing and frozen checkpoint identity before scoring V."""
import contextlib
import hashlib
import io
import json
from pathlib import Path

import effstats as es
import r2_gate

HERE = Path(__file__).resolve().parent
outdir = HERE / 'out_r2_validation'
frozen = json.loads((HERE/'round2_frozen_selection.json').read_text())
labels = ['sweep','bandit'] + list(frozen['finalists'])
expected_seeds = frozen['validation_seeds']
for label, item in frozen['finalists'].items():
    directory = item['source'].split('cand:bandit:')[-1]
    for s in 'ABCDEFG':
        path = HERE / directory / s / 'agent.npz'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['checkpoint_sha256'][s], f'checkpoint changed: {path}'
for s in 'ABCDEFG':
    for h in (80,160,400,0):
        for label in labels:
            path = outdir / f'{s}__h{h}_{label}.json'
            record = json.loads(path.read_text())
            assert record['spec']['seeds'] == expected_seeds, f'spec seeds: {path}'
            assert sorted(r['seed'] for r in record['per_episode']) == expected_seeds, f'episode seeds: {path}'
            assert record['spec']['scenario'] == s and record['spec']['horizon'] == h and record['spec']['label'] == label
            if h:
                assert all(r['steps'] == h for r in record['per_episode']), f'length mismatch: {path}'
D = es.load_dir(outdir)
verdicts = {}
for label in frozen['finalists']:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        passed, checks = r2_gate.gate(D,label,'bandit')
    (HERE/f'validation_gate_{label}.md').write_text(output.getvalue())
    objective = min(es.mean_ratio(D,label,'bandit',h)[0] for h in (80,160))
    verdicts[label] = {'passed': bool(passed), 'checks': {k:bool(v) for k,v in checks.items()}, 'objective':objective}
    print(f'{label}: {"PASS" if passed else "FAIL"}, min ratio {objective:.3f}; {verdicts[label]["checks"]}')
eligible = [label for label,record in verdicts.items() if record['passed']]
chosen = max(eligible,key=lambda label:verdicts[label]['objective']) if eligible else None
summary = {'data_check':'140 result files; 20 correctly paired worlds per cell; frozen checkpoints unchanged',
           'verdicts':verdicts,'chosen':chosen,'confirmation_authorized_by_procedure':chosen is not None}
(HERE/'round2_validation_summary.json').write_text(json.dumps(summary,indent=2))
print(f'CHOSEN: {chosen}; reserve confirmation {"required" if chosen else "not run (none passed validation)"}')
