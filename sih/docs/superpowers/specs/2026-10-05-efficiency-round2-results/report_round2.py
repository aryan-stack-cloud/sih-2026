"""Condense the validated result while retaining all gate details in separate files."""
import hashlib
import json
from pathlib import Path
import effstats as es

HERE = Path(__file__).resolve().parent
D = es.load_dir('out_r2_validation')
frozen = json.loads((HERE/'round2_frozen_selection.json').read_text())
summary = json.loads((HERE/'round2_validation_summary.json').read_text())
live_root = Path('C:/Users/This PC/Documents/codex and claude/sih/Ai-ml-1-Scheduler-Engine/ml/checkpoints')
backup_root = Path('C:/w/backup/ml-checkpoints-live-pre-efficiency-20261004')
live = json.loads((live_root/'index.json').read_text())
backup = json.loads((backup_root/'index.json').read_text())
refs = {}
for s in 'ABCDEFG':
    record = json.loads((HERE/'out_r2_validation'/f'{s}__h80_bandit.json').read_text())
    model_id = record['spec']['model']
    assert all(json.loads((HERE/'out_r2_validation'/f'{s}__h{h}_bandit.json').read_text())['spec']['model'] == model_id for h in (160,400,0))
    old_id = json.loads((HERE/'out_base'/f'{s}__h80_bandit.json').read_text())['spec']['model']
    assert old_id == model_id, f'reference changed since tuning: {s}'
    checkpoint = live[model_id]['checkpoint']
    digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(live_root/checkpoint) == digest(backup_root/backup[model_id]['checkpoint'])
    refs[s] = {'model_id':model_id,'checkpoint_sha256':digest(live_root/checkpoint)}
(HERE/'round2_reference_identity.json').write_text(json.dumps(refs,indent=2))

lines = ['# Round-2 offline result', '', 'All three Bandit finalists FAIL validation. No model selected; reserve seeds 22000–22019 remain unused by round 2. No Q-learning finalist met the tuning prerequisite.', '',
         '## Scenario B: listening efficiency on validation worlds', '',
         '| Bandit arm | 80 steps | 160 steps | 400 steps | Full |', '|---|---|---|---|---|']
for label in ['bandit']+list(frozen['finalists']):
    eff = [100*es.point(D['B',h,label],'eff') for h in (80,160,400,0)]
    lines.append(f'| `{label}` | ' + ' | '.join(f'{v:.2f}%' for v in eff) + ' |')
lines.extend(['','## Finalist verdicts','','| Arm | Mean ratio 80 / 160 | Scenario B ratio 80 / 160 | Full-run mean HPDR difference [95%], pp | Failed checks |','|---|---|---|---|---|'])
for label,verdict in summary['verdicts'].items():
    mean = [es.mean_ratio(D,label,'bandit',h) for h in (80,160)]
    b = [es.cell_ratio(D,label,'bandit','B',h) for h in (80,160)]
    hp = es.mean_diff(D,label,'bandit',0,'hpdr')
    summary['verdicts'][label].update({'ratios_mean':mean,'ratios_B':b,'hpdr_full':hp})
    failed = ', '.join(k for k,v in verdict['checks'].items() if not v)
    fmt = lambda values:' / '.join(f'{v[0]:.3f}' for v in values)
    lines.append(f'| `{label}` | {fmt(mean)} | {fmt(b)} | {hp[0]:+.2f} [{hp[1]:+.2f}, {hp[2]:+.2f}] | {failed} |')
lines.extend(['','Validation: seeds 23000–23019, 20 paired worlds per scenario and horizon, 140 result files / 2,800 evaluation episodes. All expected files, seed identities, short-run lengths and frozen candidate hashes checked. Bandit reference IDs match tuning; live checkpoint bytes match the pre-rollout backup.','',
              'The strongest candidate passes efficiency and distinct-burst guards, but full-run high-priority detection fails even the relaxed round-2 margin. This result does not pass the full gate and is not a reserve confirmation.', '',
              'Q-learning: best weaker-horizon tuning ratios versus original are 1.078 on B and 1.150 on F, permitting different recipes. Phase variants did not solve the short-run target. No claim of a universal algorithm ceiling is justified. Ground-truth oracle diagnostics are for ceilings only and were never inputs to a candidate policy.', '',
              'Verified 110 relevant tests (82 options/alignment and 28 agents/served-session). Engine/prototype parity compares three combinations, all learned parameters and 120 greedy actions per case. Experimental code and reports remain on feat/efficiency-round2; defaults and live deployments unchanged.'])
(HERE/'round2_result.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
(HERE/'round2_validation_summary.json').write_text(json.dumps(summary,indent=2))
print('\n'.join(lines))
