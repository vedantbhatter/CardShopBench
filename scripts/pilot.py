"""Matched 14-day pilot; two seeds per model, $1.80 request guard per episode."""
import os,sys,json,time,hashlib,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardshopbench.agents import ModelAgent,SYSTEM,Baseline
from cardshopbench.cli import run
from cardshopbench.engine import Config
from cardshopbench.data import load_snapshot
from compatibility import MODELS
from rate_limits import request_json

class PilotAgent(ModelAgent):
 def step(self,market):
  messages=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'state':market.state(),'recent_events':market.events[-8:]})}]
  reserve=((len(json.dumps(messages).encode())+512)*self.input_rate+4096*self.output_rate)/1e6
  if self.usage['cost_usd']+reserve>self.max_cost: raise RuntimeError('Episode budget reached')
  payload={'model':self.name,'messages':messages,'max_tokens':4096,'response_format':{'type':'json_object'},'reasoning':{'effort':'low'},'provider':{'require_parameters':True,'allow_fallbacks':False,'order':[self.provider],'max_price':{'prompt':self.input_rate,'completion':self.output_rate}}}
  start=time.monotonic()
  req=urllib.request.Request(self.endpoint,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
  result=request_json(self,req,reserve,market.day)
  usage=result.get('usage',{});cost=usage.get('cost')
  if isinstance(cost,(int,float)) and cost>=0:self.usage['cost_usd']+=cost-reserve
  self.usage['prompt_tokens']+=usage.get('prompt_tokens',0);self.usage['completion_tokens']+=usage.get('completion_tokens',0)
  self.transcript.append({'day':market.day,'latency_s':time.monotonic()-start,'request':payload,'response':result})
  try:
   action=json.loads(result['choices'][0]['message']['content'])
   if not isinstance(action,dict) or not isinstance(action.get('tool'),str) or not isinstance(action.get('args',{}),dict):raise ValueError()
   return action
  except (ValueError,TypeError,KeyError):return {'tool':'invalid_model_output','args':{}}

def main():
 index=int(sys.argv[1]);model=MODELS[index]
 providers=['OpenAI','Claude Platform on AWS','Google','Relace','Darkbloom','Near AI']
 out=Path(os.environ.get('CARDSHOPBENCH_RUN_DIR','runs/pilot'));out.mkdir(parents=True,exist_ok=True)
 with urllib.request.urlopen('https://openrouter.ai/api/v1/models',timeout=30) as r:catalog={m['id']:m for m in json.load(r)['data']}
 meta=catalog[model];snap=load_snapshot('data/snapshot.json')
 for seed in [11,22]:
  a=PilotAgent(model,max_cost=1.8,input_rate=float(meta['pricing']['prompt'])*1.1e6,output_rate=float(meta['pricing']['completion'])*1.1e6);a.provider=providers[index];a.retry_events=[]
  cfg=Config(days=14,seed=seed,max_actions=6)
  result=run(snap,a,cfg,str(out/f'{index}-{seed}.checkpoint'))
  result['retry_events']=a.retry_events
  result['experiment']={'commit':os.environ.get('GITHUB_SHA'),'catalog':meta,'provider':a.provider,'reasoning_effort':'low','system_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),'research_corpus':[],'transport_revision':'paced-429-retry-v1','original_run':45282574457}
  (out/f'{index}-{seed}.json').write_text(json.dumps(result,indent=2))
  print(model,seed,result['status'],result['usage'],result['error'],flush=True)
  for name in ['cash','margin','momentum']:
   (out/f'baseline-{index}-{seed}-{name}.json').write_text(json.dumps(run(snap,Baseline(name),cfg),indent=2))
if __name__=='__main__':main()
