"""Small paid API compatibility probe; not a performance leaderboard."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cardshopbench.agents import SYSTEM
from cardshopbench.data import load_snapshot
from cardshopbench.engine import Config, Market

MODELS = ['openai/gpt-6.2-astra', 'anthropic/claude-opus-5.5',
          'google/gemini-4-neon', 'moonshotai/kimi-k3.1-pro',
          'qwen/qwen3.8-27b', 'openai/gpt-oss-120b']
OUT = Path('runs/compatibility')
MAX_OUTPUT = 4096
PER_MODEL = 0.60

def main():
    key = os.environ.get('CARDSHOPBENCH_API_KEY')
    if not key:
        raise SystemExit('Missing CARDSHOPBENCH_API_KEY repository secret')
    OUT.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen('https://openrouter.ai/api/v1/models', timeout=30) as response:
        catalog = {m['id']:m for m in json.load(response)['data']}
    snapshot = load_snapshot('data/snapshot.json')
    manifest = {'kind':'compatibility probe, not comparative performance evaluation',
                'commit':os.environ.get('GITHUB_SHA'), 'seed':11,
                'max_calls_per_model':3, 'max_output_tokens':MAX_OUTPUT,
                'reserved_budget_usd':len(MODELS)*PER_MODEL,
                'system_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),
                'snapshot_sha256':snapshot.get('sha256'), 'models':[]}
    for index, model in enumerate(MODELS):
        row = {'model':model, 'calls':[], 'status':'pending'}
        manifest['models'].append(row)
        if model not in catalog:
            row['status']='unavailable'; continue
        meta = catalog[model]
        row['catalog']=meta
        # Cap routing prices at catalog rates plus 10%; reject costlier routes.
        rate_in = float(meta['pricing']['prompt'])*1.1
        rate_out = float(meta['pricing']['completion'])*1.1
        if rate_in <= 0 or rate_out <= 0:
            row['status']='unsupported pricing'; continue
        market = Market(snapshot, Config(days=1, seed=11, max_actions=3))
        reserved = 0
        for turn in range(3):
            if market.day >= 1: break
            messages=[{'role':'system','content':SYSTEM}, {'role':'user','content':json.dumps({'state':market.state(),'recent_events':market.events[-8:]})}]
            reserve=(len(json.dumps(messages).encode())+512)*rate_in+MAX_OUTPUT*rate_out
            if reserved+reserve > PER_MODEL:
                row['status']='budget stopped'; break
            reserved += reserve # Never release reservation, even after timeout/error.
            payload={'model':model,'messages':messages,'max_tokens':MAX_OUTPUT,
                     'response_format':{'type':'json_object'},
                     'reasoning':{'effort':'low'},
                     'provider':{'require_parameters':True,'allow_fallbacks':False,
                                 'max_price':{'prompt':rate_in*1e6,'completion':rate_out*1e6}}}
            call={'turn':turn,'reserved_usd':reserve,'request':payload}
            row['calls'].append(call)
            start=time.monotonic()
            try:
                request=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=90) as response:
                    result=json.load(response)
                call['response']=result
                content=result['choices'][0]['message']['content']
                try:
                    action=json.loads(content)
                    if not isinstance(action,dict) or not isinstance(action.get('tool'),str) or not isinstance(action.get('args',{}),dict):
                        raise ValueError('Invalid action shape')
                    call['valid_json_action']=True
                    call['tool_result']=market.act(action)
                except (ValueError,TypeError,KeyError) as exc:
                    call['valid_json_action']=False
                    call['parse_error']=type(exc).__name__
                row['status']='responses received'
            except urllib.error.HTTPError as exc:
                call['error']={'type':'HTTPError','status':exc.code}
                row['status']='request failed'; break
            except Exception as exc:
                call['error']={'type':type(exc).__name__}
                row['status']='request failed'; break
            finally:
                call['latency_s']=round(time.monotonic()-start,3)
        row['reserved_usd']=reserved
        row['events']=market.events
        (OUT/f'model-{index}.json').write_text(json.dumps(row,indent=2))
        print(model,row['status'],len(row['calls']),flush=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    lines=['# API compatibility checks','', 'These short probes are not business-performance evaluations.','', '| Model | Status | Calls | Valid JSON actions | Reported cost |','|---|---|---:|---:|---:|']
    for row in manifest['models']:
        calls=row['calls']; costs=[c.get('response',{}).get('usage',{}).get('cost') for c in calls]
        cost=f"${sum(costs):.6f}" if costs and all(isinstance(c,(int,float)) for c in costs) else 'unavailable'
        lines.append(f"| {row['model']} | {row['status']} | {len(calls)} | {sum(c.get('valid_json_action',False) for c in calls)} | {cost} |")
    report='\n'.join(lines)+'\n'
    (OUT/'SUMMARY.md').write_text(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f: f.write(report)

if __name__=='__main__': main()
