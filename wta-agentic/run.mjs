import {mkdirSync,writeFileSync,appendFileSync,readFileSync,readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join,dirname} from 'node:path';
import {scenarios,initialTask,SYSTEM,VERSION} from './scenarios.mjs';
import {Sandbox,toolsFor,hash} from './sandbox.mjs';
import {grade} from './grade.mjs';
import {Budget} from './budget.mjs';
import {Router,getJSON,rates} from './openrouter.mjs';
export const CANDIDATES=[{id:'openai/gpt-6.1-sol',tag:'openai'},{id:'anthropic/claude-opus-5.5',tag:'claude-on-aws'},{id:'deepseek/deepseek-v4.1-flash-1017',tag:'deepseek'},{id:'qwen/qwen3.7-plus',tag:'alibaba'}];
export async function episode(s,profile,generate,{maxSteps=12,maxMs=180000}={}){
 const box=new Sandbox(s),tools=toolsFor(s.family),messages=[{role:'system',content:SYSTEM},{role:'user',content:JSON.stringify(initialTask(s))}],start=Date.now();let calls=0,cost=0,error=null;const trace=[];
 try{for(let step=0;step<maxSteps;step++){
  if(Date.now()-start>maxMs)throw Error('episode_timeout');
  const promptHash=hash({messages,tools});const result=await generate(profile,messages,tools,{scenarioId:s.id,step,promptHash});calls++;cost+=result.cost??0;trace.push({step,promptHash,response:result.message,requestId:result.requestId,cost:result.cost});
  const message=result.message;messages.push(message);
  if(!Array.isArray(message.tool_calls)||!message.tool_calls.length){error='ended_without_finish_tool';break;}
  if(message.tool_calls.length>8)throw Error('parallel_tool_cap');
  for(const t of message.tool_calls){let args;try{args=JSON.parse(t.function.arguments);}catch{args=null;}
   const out=box.call(t.function.name,args);messages.push({role:'tool',tool_call_id:t.id,content:JSON.stringify(out)});
   if(box.state.final)break;
  }
  if(box.state.final)break;
 }if(!box.state.final&&!error)error='step_cap';}catch(e){error=e.message;}
 return {scenarioId:s.id,seed:s.seed,split:s.split,family:s.family,model:profile.id,calls,cost,latencyMs:Date.now()-start,error,grade:grade(box),state:box.state,audit:box.audit,initialMessages:messages.slice(0,2),trace:trace.map(t=>({...t,response:t.response?{role:t.response.role,content:t.response.content,tool_calls:t.response.tool_calls}:null}))};
}
const quantile=(rows,q)=>rows.length?[...rows].sort((a,b)=>a-b)[Math.ceil(rows.length*q)-1]:null;
export function summarize(results,attempts,budget){return CANDIDATES.map(p=>{const rows=results.filter(r=>r.model===p.id),paid=attempts.filter(a=>a.requestedModel===p.id),success=rows.filter(r=>r.grade.accepted).length,completed=rows.filter(r=>r.grade.businessCompleted).length,billed=paid.reduce((n,a)=>n+(a.cost??0),0);return {model:p.id,episodes:rows.length,accepted:success,businessCompleted:completed,correctRefusals:rows.filter(r=>r.grade.correctRefusal).length,correctBlocks:rows.filter(r=>r.grade.correctBlocked).length,correctTentative:rows.filter(r=>r.grade.correctAwaitingApproval).length,successRate:rows.length?success/rows.length:null,cost:billed,costPerAccepted:success?billed/success:null,costPerBusinessCompleted:completed?billed/completed:null,policyViolations:rows.reduce((n,r)=>n+r.grade.policyViolations,0),invalidTools:rows.reduce((n,r)=>n+r.grade.invalidCalls,0),unnecessaryQuestions:rows.reduce((n,r)=>n+r.grade.unnecessaryQuestions,0),recovered:rows.filter(r=>r.grade.recovered).length,injectedFailures:rows.reduce((n,r)=>n+r.grade.injectedFailures,0),toolCalls:rows.reduce((n,r)=>n+r.grade.toolCalls,0),p50Ms:quantile(rows.map(r=>r.latencyMs),.5),p95Ms:quantile(rows.map(r=>r.latencyMs),.95),inferenceRequests:paid.length,unknownCosts:paid.filter(a=>a.cost===null).length,reasoningTokens:paid.reduce((n,a)=>n+(a.usage?.completion_tokens_details?.reasoning_tokens??0),0),families:Object.fromEntries([...new Set(rows.map(r=>r.family))].map(f=>[f,{n:rows.filter(r=>r.family===f).length,accepted:rows.filter(r=>r.family===f&&r.grade.accepted).length}])),budgetConservativeTotal:budget.spent};});}
async function main(){
 const mode=process.argv[2]??'offline',out=process.argv[3]??'benchmarks/runs/agentic';mkdirSync(out,{recursive:true});
 if(mode!=='live')throw Error('Use tests for offline verification; only live mode measures models.');
 if(process.env.GITHUB_ACTIONS!=='true'||process.env.GITHUB_RUN_ATTEMPT!=='1'||process.env.WTA_PILOT_CLAIM!=='wta-agentic-usd25-v1')throw Error('Live execution requires purpose-built first-attempt Actions claim');
 const key=process.env.CARDSHOPBENCH_API_KEY;if(!key)throw Error('missing_actions_secret');
 const budget=new Budget(join(out,'ledger.jsonl'),25),attempts=[],results=[];if(budget.entries.length)throw Error('Refusing restart of a prior ledger: unknown pending spend must be retained');
 const save=(name,x)=>writeFileSync(join(out,name),JSON.stringify(x,null,2));
 const catalog=await getJSON('models');save('catalogue.json',catalog);
 const kd=(await getJSON('key',key)).data;
 const available=kd?.limit_remaining;if(!Number.isFinite(available)||available<25)throw Error('Key must expose at least $25 verified remaining limit before the pilot');
 save('account-budget.json',{limit:kd.limit,limit_remaining:available,usage:kd.usage});
 const profiles=[];for(const c of CANDIDATES){const model=catalog.data.find(m=>m.id===c.id);if(!model?.supported_parameters?.includes('tools'))throw Error('model_tools_unavailable');const endpoints=await getJSON(`models/${c.id}/endpoints`);save(c.id.replaceAll('/','-')+'-endpoints.json',endpoints);const endpoint=endpoints.data.endpoints.find(e=>e.tag===c.tag&&e.status===0);if(!endpoint)throw Error(`pin_unavailable:${c.tag}`);const price=rates(endpoint);if(price.prompt>0.000005||price.completion>0.000025)throw Error('price_cap');profiles.push({...c,rates:price,endpoint,model});}
 const dir=dirname(fileURLToPath(import.meta.url));const sourceHashes=Object.fromEntries(readdirSync(dir).filter(n=>n.endsWith('.mjs')).map(n=>[n,hash(readFileSync(join(dir,n),'utf8'))]));
 const manifest={version:VERSION,startedAt:new Date().toISOString(),commit:process.env.GITHUB_SHA,runId:process.env.GITHUB_RUN_ID,node:process.version,sourceHashes,systemHash:hash(SYSTEM),scenarioHash:hash([scenarios(11),scenarios(22)]),settings:{maxOutputTokens:2048,reasoningEffort:'low',maxSteps:12,timeoutMs:60000,maxEpisodeMs:180000,maxRequests:1300,retries:0,providerFallbacks:false,temperature:'provider default',samplingSeed:'not supplied; experiment seeds generate fixtures and order only'},budget:{authorized:25,smokeStop:2,matrixStop:22,contingency:3,reruns:'permanent tag claim denies any second run'},profiles,phases:[],status:'running'};save('manifest.json',manifest);
 const router=new Router({key,budget,log:a=>{attempts.push(a);appendFileSync(join(out,'attempts.jsonl'),JSON.stringify(a)+'\n');}});
 const compatible=[];budget.limit=2;
 try{
  // Real native call and tool observation; neutral compatibility only, excluded from task success denominator.
  for(const p of profiles){if(budget.spent>1.5)throw Error('smoke_stage_budget');const messages=[{role:'system',content:'Compatibility test: call probe with value 7. After tool observation, say done.'},{role:'user',content:'Run the probe.'}],tools=[{type:'function',function:{name:'probe',description:'Returns a synthetic observation.',parameters:{type:'object',properties:{value:{type:'integer'}},required:['value'],additionalProperties:false}}}];let okay=false,smokeError=null;try{const a=await router.generate(p,messages,tools,{phase:'smoke',promptHash:hash(messages)});const tc=a.message.tool_calls?.[0];if(tc?.function?.name!=='probe'||JSON.parse(tc.function.arguments).value!==7)throw Error('smoke_native_tool_invalid');messages.push(a.message,{role:'tool',tool_call_id:tc.id,content:'{"observed":7}'});const b=await router.generate(p,messages,tools,{phase:'smoke',promptHash:hash(messages)});okay=!!b.message.content&&!b.message.tool_calls?.length;if(!okay)throw Error('smoke_observation_invalid');}catch(e){smokeError=e.message;if(budget.unknown)throw e;}manifest.phases.push({phase:'smoke',model:p.id,compatible:okay,error:smokeError});if(okay)compatible.push(p);save('manifest.json',manifest);}
  const before=budget.spent;if(before>2)throw Error('smoke_stage_budget');budget.limit=22;
  // Seed 11 is development. Seed 22 is held out and repeated twice with unchanged prompt/settings.
  const matrix=[...scenarios(11).map(s=>({...s,repetition:0})),...scenarios(22).map(s=>({...s,repetition:0})),...scenarios(22).map(s=>({...s,repetition:1}))];
  // Seeded deterministic interleaving; rotate model order to reduce time/order confounding.
  matrix.sort((a,b)=>hash(`${a.id}-${a.repetition}`).localeCompare(hash(`${b.id}-${b.repetition}`)));
  for(let i=0;i<matrix.length;i++){
   const s=matrix[i];for(let j=0;j<compatible.length;j++){
    if(budget.spent>=22)throw Error('matrix_stage_budget');const p=compatible[(i+j)%compatible.length];const prior=budget.spent;
    const r=await episode(s,p,(...args)=>{if(budget.spent-prior>1.2)throw Error('episode_cost_cap');return router.generate(...args);});r.repetition=s.repetition;r.cost=budget.spent-prior;results.push(r);appendFileSync(join(out,'episodes.jsonl'),JSON.stringify(r)+'\n');
    console.log(JSON.stringify({model:p.id,scenario:s.id,rep:s.repetition,accepted:r.grade.accepted,error:r.error,budgetUsed:budget.spent}));
    save('summary.json',summarize(results,attempts,budget));if(budget.unknown||r.error==='budget_exhausted'||r.error==='request_cap')throw Error(r.error??'accounting_unknown');
   }
  }
  manifest.status='complete';
 }catch(e){manifest.status='stopped';manifest.error=e.message;}
 finally{manifest.endedAt=new Date().toISOString();manifest.budget.conservativeUsed=budget.spent;manifest.budget.billed=attempts.reduce((n,a)=>n+(a.cost??0),0);manifest.budget.unknownAttempts=attempts.filter(a=>a.cost===null).length;manifest.budget.calls=router.calls;save('manifest.json',manifest);save('summary.json',summarize(results,attempts,budget));console.log(JSON.stringify({status:manifest.status,budget:manifest.budget,error:manifest.error}));}
 if(manifest.status!=='complete')process.exitCode=1;
}
if(process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1])main().catch(e=>{console.error('Pilot stopped:',e.message);process.exitCode=1;});
