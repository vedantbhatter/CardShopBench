import {reservation} from './budget.mjs';
const finite=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
export async function getJSON(path,key=null){const r=await fetch('https://openrouter.ai/api/v1/'+path,{headers:key?{Authorization:`Bearer ${key}`}:{},signal:AbortSignal.timeout(20000),redirect:'error'});if(!r.ok)throw Error(`metadata_http_${r.status}`);return r.json();}
export function rates(endpoint){const p=endpoint.pricing,keys=['prompt','completion'];if(!p||keys.some(k=>typeof p[k]!=='string'||!Number.isFinite(Number(p[k]))||Number(p[k])<0))throw Error('unknown_prices');if(Number(p.request??0)!==0)throw Error('unpriced_request_fee');const eligible=[p,...(p.overrides??[]).filter(o=>!o.min_prompt_tokens||o.min_prompt_tokens<=90000)];return {prompt:Math.max(...eligible.map(o=>Number(o.prompt??p.prompt))),completion:Math.max(...eligible.map(o=>Number(o.completion??p.completion)))};}
export class Router{
 constructor({key,budget,log,fetcher=fetch}){this.key=key;this.budget=budget;this.log=log;this.fetcher=fetcher;this.calls=0;}
 async generate(profile,messages,tools,meta){
  if(++this.calls>1300)throw Error('request_cap');const body={model:profile.id,messages,tools,tool_choice:'auto',max_tokens:2048,reasoning:{effort:'low'},provider:{only:[profile.tag],allow_fallbacks:false,require_parameters:true,max_price:{prompt:profile.rates.prompt*1e6,completion:profile.rates.completion*1e6}},usage:{include:true}};
  const id=`call-${this.calls}`,reserved=reservation(body,profile.rates);this.budget.reserve(id,reserved);const start=Date.now();let json=null,error=null,status=null;
  try{const r=await this.fetcher('https://openrouter.ai/api/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${this.key}`,'Content-Type':'application/json','X-Title':'Synthetic workflow agentic evaluation'},body:JSON.stringify(body),signal:AbortSignal.timeout(60000),redirect:'error'});status=r.status;json=await r.json();if(!r.ok||json.error)error=`inference_http_${r.status}_${json.error?.code??'error'}`;}catch{error='transport_or_timeout';}
  const latencyMs=Date.now()-start;let cost=finite(json?.usage?.cost)?json.usage.cost:null,generation=null;
  // Reconcile every generation against OpenRouter's billed record. Bounded metadata reads, never inference retries.
  if(json?.id){for(let attempt=0;attempt<3;attempt++){try{const r=await this.fetcher(`https://openrouter.ai/api/v1/generation?id=${encodeURIComponent(json.id)}`,{headers:{Authorization:`Bearer ${this.key}`},signal:AbortSignal.timeout(10000),redirect:'error'});if(r.ok){const d=(await r.json()).data;if(finite(d?.total_cost)){generation={id:d.id,total_cost:d.total_cost,model:d.model,provider_name:d.provider_name,native_tokens_prompt:d.native_tokens_prompt,native_tokens_completion:d.native_tokens_completion,native_tokens_reasoning:d.native_tokens_reasoning};cost=Math.max(cost??0,d.total_cost);break;}}}catch{}if(attempt<2)await new Promise(r=>setTimeout(r,600));}}
  const result={id,...meta,requestedModel:profile.id,resolvedModel:json?.model??null,provider:json?.provider??generation?.provider_name??null,requestId:json?.id??null,usage:json?.usage??null,generation,cost,reserved,latencyMs,status,error,finishReason:json?.choices?.[0]?.finish_reason??null,message:json?.choices?.[0]?.message??null,promptHash:meta.promptHash};
  // Never persist headers/key or arbitrary provider error bodies. Synthetic message content only; reasoning omitted.
  if(result.message)result.message={role:'assistant',content:result.message.content??null,tool_calls:result.message.tool_calls??undefined,...(result.message.reasoning_details?{reasoning_details:result.message.reasoning_details}:{} )};
  this.log({...result,message:result.message?{role:result.message.role,content:result.message.content,tool_calls:result.message.tool_calls}:null});
  this.budget.settle(id,reserved,cost);if(error)throw Error(error);
  if(json.model!==profile.id)throw Error('resolved_model_mismatch');
  if(!generation){this.budget.unknown=true;throw Error('generation_reconciliation_unknown');}
  if(!result.message||!['tool_calls','stop'].includes(result.finishReason))throw Error('incomplete_response');return result;
 }
}
