"""Tuning-world occupancy ceilings, without exposing ground truth to a learned policy."""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.environ['EFF_ENGINE'])
from ml.environments.environment import make_env
from ml.utils.config import load_scenario

summary = json.loads((HERE/'q_round2_tuning_summary.json').read_text())
out = []
print('| scenario | steps | original Q | +20% target | best fixed window, hindsight | clairvoyant best each step |')
print('|---|---|---|---|---|---|')
for s in 'BF':
    for h in (80,160):
        cfg = dict(load_scenario(s), duration_steps=h)
        k = cfg['receiver']['bandwidth_k']
        fixed, oracle = [], []
        for seed in range(20000,20020):
            env = make_env(cfg, seed=seed)
            env.reset(seed=seed)
            occ = env.ground_truth.occupancy[:h].astype(np.int32)
            counts = sum(np.roll(occ,-j,axis=1) for j in range(k))
            fixed.append(float(counts.mean(axis=0).max()/k))
            oracle.append(float(counts.max(axis=1).mean()/k))
        old = summary[s]['q']['eff'][(80,160).index(h)]
        f,o = 100*float(np.mean(fixed)),100*float(np.mean(oracle))
        out.append({'scenario':s,'horizon':h,'original_eff_percent':old,'target_percent':1.2*old,
                    'hindsight_fixed_percent':f,'clairvoyant_percent':o})
        print(f'| {s} | {h} | {old:.2f}% | {1.2*old:.2f}% | {f:.2f}% | {o:.2f}% |')
(HERE/'q_round2_ceiling.json').write_text(json.dumps(out,indent=2))
