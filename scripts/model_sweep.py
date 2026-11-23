"""Run explicit model × seed pilots; no keys are embedded or persisted."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardshopbench.agents import ModelAgent
from cardshopbench.cli import run
from cardshopbench.data import load_snapshot
from cardshopbench.engine import Config
p=argparse.ArgumentParser()
p.add_argument('--models',nargs='+',required=True)
p.add_argument('--input-rates',nargs='+',type=float,required=True)
p.add_argument('--output-rates',nargs='+',type=float,required=True)
p.add_argument('--max-cost-per-run',type=float,default=1)
p.add_argument('--seeds',nargs='+',type=int,default=[11,22,33,44,55])
p.add_argument('--days',type=int,default=5)
p.add_argument('--snapshot',default='data/snapshot.json')
p.add_argument('--out',default='runs/sweep')
a=p.parse_args()
if len(a.models)!=len(a.input_rates) or len(a.models)!=len(a.output_rates): p.error('One pair of rates per model required')
snapshot=load_snapshot(a.snapshot); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
print(f'Planned request-guard budgets total: ${len(a.models)*len(a.seeds)*a.max_cost_per_run:.2f}; provider-side limits remain recommended.',flush=True)
results=[]
for i,model in enumerate(a.models):
 for seed in a.seeds:
  agent=ModelAgent(model,input_rate=a.input_rates[i],output_rate=a.output_rates[i],max_cost=a.max_cost_per_run)
  result=run(snapshot,agent,Config(seed=seed,days=a.days),str(out/f'model-{i}-seed-{seed}.checkpoint'))
  (out/f'model-{i}-seed-{seed}.json').write_text(json.dumps(result,indent=2))
  results.append({k:result[k] for k in ('agent','status','error','summary','usage')})
  print(model,seed,result['status'],flush=True)
(out/'summary.json').write_text(json.dumps(results,indent=2))
