import {reservation} from './budget.mjs';
const finite=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
export async function getJSON(path,key=null){const r=await fetch('https://openrouter.ai/api/v1/'+path,{headers:key?{Authorization:`Bearer ${key}`}:{},signal:AbortSignal.timeout(20000),redirect:'error'});if(!r.ok)throw Error(`metadata_http_${r.status}`);return r.json();}
export function rates(endpoint){const p=endpoint.pricing,keys=['prompt','completion'];if(!p||keys.some(k=>typeof p[k]!=='string'||!Number.isFinite(Number(p[k]))||Number(p[k])<0))throw Error('unknown_prices');if(Number(p.request??0)!==0)throw Error('unpriced_request_fee');const eligible=[p,...(p.overrides??[]).filter(o=>!o.min_prompt_tokens||o.min_prompt_tokens<=90000)];return {prompt:Math.max(...eligible.map(o=>Number(o.prompt??p.prompt))),completion:Math.max(...eligible.map(o=>Number(o.completion??p.completion)))};}
export class Router{
 constructor({key,budget,log,billingLog=()=>{},fetcher=fetch,initialKeyUsage=null,initialCalls=0}){this.key=key;this.budget=budget;this.log=log;this.billingLog=billingLog;this.fetcher=fetcher;this.calls=initialCalls;this.pending=[];this.deferred=[];this.expectedKeyUsage=initialKeyUsage;}
 async reconcileOne(item,{final=false}={}){
  const {result,logged,reserved}=item;let generation=null;
  const tries=item.unsettled||final?6:2;
  for(let attempt=0;attempt<tries;attempt++){
   try{const r=await this.fetcher(`https://openrouter.ai/api/v1/generation?id=${encodeURIComponent(result.requestId)}`,{headers:{Authorization:`Bearer ${this.key}`},signal:AbortSignal.timeout(10000),redirect:'error'});if(r.ok){const d=(await r.json()).data;if(finite(d?.total_cost)){generation={id:d.id,total_cost:d.total_cost,model:d.model,provider_name:d.provider_name,native_tokens_prompt:d.native_tokens_prompt,native_tokens_completion:d.native_tokens_completion,native_tokens_reasoning:d.native_tokens_reasoning};break;}}}catch{}
   if(attempt<tries-1)await new Promise(r=>setTimeout(r,Math.min(8000,500*2**attempt)));
  }
  if(!generation){if(finite(result.cost)){if(!item.heldExtra){this.budget.record({id:result.id,event:'pending_generation_reserve',delta:Math.max(0,reserved-result.cost),reserved,knownUsageCost:result.cost});item.heldExtra=true;}result.pendingGeneration=true;logged.pendingGeneration=true;this.deferred.push(item);this.billingLog({id:result.id,event:'generation_pending',knownUsageCost:result.cost,reserved});return;}this.budget.quarantine(result.id,reserved,'No billed usage or generation record; full bounded charge retained, no business actions from this response');this.billingLog({id:result.id,event:'generation_unknown',reserved});throw Error('unknown_charge_quarantined');}
  const reconciled=Math.max(result.cost??0,generation.total_cost),delta=reconciled-(result.cost??0);
  if(item.unsettled)this.budget.settle(result.id,reserved,reconciled);
  else if(item.heldExtra){this.budget.record({id:result.id,event:'pending_generation_settled',delta:reconciled-reserved,cost:reconciled});if(finite(this.expectedKeyUsage))this.expectedKeyUsage+=delta;}else if(delta>0){this.budget.record({id:result.id,event:'generation_adjustment',delta,cost:reconciled});if(finite(this.expectedKeyUsage))this.expectedKeyUsage+=delta;}
  Object.assign(result,{generation,pendingGeneration:false,cost:reconciled,provider:result.provider??generation.provider_name});Object.assign(logged,{generation,pendingGeneration:false,cost:reconciled,provider:result.provider});
  this.billingLog({id:result.id,event:'generation_reconciled',generation,cost:reconciled});
  if(reconciled>reserved+1e-8){this.budget.unknown=true;throw Error('reservation_exceeded');}
 }
 async reconcilePending({final=false}={}){const pending=[...this.pending.splice(0),...this.deferred.splice(0)];const settled=await Promise.allSettled(pending.map(i=>this.reconcileOne(i,{final}))); const failure=settled.find(s=>s.status==='rejected');if(failure)throw failure.reason;}
 async generate(profile,messages,tools,meta){
  if(++this.calls>1300)throw Error('request_cap');const body={model:profile.id,messages,tools,tool_choice:'auto',max_tokens:2048,reasoning:{effort:'low'},provider:{only:[profile.tag],allow_fallbacks:false,require_parameters:true,max_price:{prompt:profile.rates.prompt*1e6,completion:profile.rates.completion*1e6}},usage:{include:true}};
  const id=`call-${this.calls}`,reserved=reservation(body,profile.rates);this.budget.reserve(id,reserved);const start=Date.now();let json=null,error=null,status=null;
  try{const r=await this.fetcher('https://openrouter.ai/api/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${this.key}`,'Content-Type':'application/json','X-Title':'Synthetic workflow agentic evaluation'},body:JSON.stringify(body),signal:AbortSignal.timeout(60000),redirect:'error'});status=r.status;json=await r.json();if(!r.ok||json.error)error=`inference_http_${r.status}_${json.error?.code??'error'}`;}catch{error='transport_or_timeout';}
  const latencyMs=Date.now()-start;let cost=finite(json?.usage?.cost)?json.usage.cost:null,counterReconciliation=null;
  // A rejected pre-inference 404 with no generation can be reconciled as unbilled ONLY when
  // the current key's cumulative usage exactly matches all known billed calls since baseline.
  if([404,429].includes(status)&&!json?.id&&finite(this.expectedKeyUsage)){
   try{const r=await this.fetcher('https://openrouter.ai/api/v1/key',{headers:{Authorization:`Bearer ${this.key}`},signal:AbortSignal.timeout(10000),redirect:'error'});const d=r.ok?(await r.json()).data:null;if(finite(d?.usage)&&Math.abs(d.usage-this.expectedKeyUsage)<1e-8){cost=0;counterReconciliation={expectedUsage:this.expectedKeyUsage,observedUsage:d.usage,reason:`pre-inference ${status} without generation; exact cumulative key usage reconciliation`};}}catch{}
  }
  const result={id,...meta,requestedModel:profile.id,resolvedModel:json?.model??null,provider:json?.provider??null,requestId:json?.id??null,usage:json?.usage??null,generation:null,counterReconciliation,cost,reserved,latencyMs,status,error,errorMessage:typeof json?.error?.message==='string'?json.error.message.replaceAll(this.key,'[REDACTED]').slice(0,500):null,finishReason:json?.choices?.[0]?.finish_reason??null,message:json?.choices?.[0]?.message??null};
  if(result.message)result.message={role:'assistant',content:result.message.content??null,tool_calls:result.message.tool_calls??undefined,...(result.message.reasoning_details?{reasoning_details:result.message.reasoning_details}:{} )};
  const logged={...result,message:result.message?{role:result.message.role,content:result.message.content,tool_calls:result.message.tool_calls}:null};this.log(logged);
  const item={result,logged,reserved,unsettled:cost===null};
  if(cost===null){if(result.requestId)await this.reconcileOne(item);else {this.budget.quarantine(id,reserved,error??'Missing billed usage');throw Error(error??'unknown_charge_quarantined');}}
  else {this.budget.settle(id,reserved,cost);if(finite(this.expectedKeyUsage))this.expectedKeyUsage+=cost;if(result.requestId)this.pending.push(item);}
  if(error)throw Error(error);
  if(Number.isFinite(json?.usage?.completion_tokens)&&json.usage.completion_tokens>body.max_tokens){this.budget.unknown=true;throw Error('provider_output_cap_exceeded');}
  if(json.model!==profile.id)throw Error('resolved_model_mismatch');
  if(!result.message||!['tool_calls','stop'].includes(result.finishReason))throw Error('incomplete_response');return result;
 }
}
