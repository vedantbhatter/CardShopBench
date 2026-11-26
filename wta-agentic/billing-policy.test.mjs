import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {Budget} from './budget.mjs';
import {Router} from './openrouter.mjs';
test('known primary billed cost with delayed supplemental metadata retains full reserve, then refunds on reconciliation',async()=>{
 const dir=mkdtempSync(join(tmpdir(),'billing-delay-'));try{
  const budget=new Budget(join(dir,'ledger'),1),log=[],events=[];let available=false;
  const fetcher=async url=>new Response(JSON.stringify(url.includes('/generation?')?(available?{data:{id:'g1',total_cost:.015,model:'m',provider_name:'Pinned'}}:{error:{message:'Not found'}}):{id:'g1',model:'m',provider:'Pinned',usage:{cost:.01},choices:[{finish_reason:'stop',message:{role:'assistant',content:'done'}}]}),{status:url.includes('/generation?')&&!available?404:200});
  const router=new Router({key:'test',budget,log:x=>log.push(x),billingLog:x=>events.push(x),fetcher});
  await router.generate({id:'m',tag:'pin',rates:{prompt:.000004,completion:.00002}},[],[],{});
  await router.reconcilePending();assert.equal(budget.unknown,false);assert.equal(router.deferred.length,1);assert.equal(log[0].cost,.01);assert.equal(log[0].pendingGeneration,true);assert.ok(Math.abs(budget.spent-log[0].reserved)<1e-9);
  available=true;await router.reconcilePending();assert.equal(router.deferred.length,0);assert.equal(log[0].cost,.015);assert.equal(log[0].pendingGeneration,false);assert.ok(Math.abs(budget.spent-.015)<1e-9);assert.equal(events.at(-1).event,'generation_reconciled');
 }finally{rmSync(dir,{recursive:true});}
});
test('an uncertain bounded charge keeps its full maximum, executes no actions, and cannot be refunded by inventing an amount',()=>{const d=mkdtempSync(join(tmpdir(),'bounded-charge-'));try{const b=new Budget(join(d,'ledger'),1);b.reserve('x',.6);b.quarantine('x',.6,'transport timeout');assert.equal(b.spent,.6);assert.throws(()=>b.reserve('next',.5),/budget_exhausted/);assert.throws(()=>b.quarantine('invented',.1,'no reservation'),/unknown_budget_exposure/);assert.equal(b.unknown,true);}finally{rmSync(d,{recursive:true});}});
import {claimCampaign,completeCampaign} from './budget.mjs';
test('durable campaign claim prevents a fresh output folder from resetting the $25 authorization',()=>{const d=mkdtempSync(join(tmpdir(),'campaign-claim-'));try{const p=join(d,'claim.json');claimCampaign(p,{out:'run-a',priorKnown:.5,priorReserved:.1,authorizedCeiling:25});assert.throws(()=>claimCampaign(p,{out:'run-b',priorKnown:0}),/campaign_already_claimed/);completeCampaign(p,{status:'complete',budget:{conservativeUsed:2}});assert.throws(()=>claimCampaign(p,{out:'run-c'}),/campaign_already_claimed/);}finally{rmSync(d,{recursive:true});}});
import {writeFileSync,mkdirSync} from 'node:fs';
import {continueCampaign} from './budget.mjs';
test('continuation requires complete prior ledger and exact prior attempts, then carries the same authorization forward',()=>{const d=mkdtempSync(join(tmpdir(),'campaign-resume-'));try{const run=join(d,'old'),claim=join(d,'claim');mkdirSync(run);const a=[{id:'a',cost:.3}];writeFileSync(join(run,'attempts-final.json'),JSON.stringify(a));writeFileSync(join(run,'ledger.jsonl'),JSON.stringify({delta:.3})+'\n');claimCampaign(claim,{out:run,authorizedCeiling:25});const metadata={out:join(d,'new'),priorOut:run,authorizedCeiling:25,carriedConservative:.3};assert.throws(()=>continueCampaign(claim,metadata,a),/not_verified/);completeCampaign(claim,{status:'complete',budget:{conservativeUsed:.3}});assert.throws(()=>continueCampaign(claim,{...metadata,carriedConservative:0},a),/cost_mismatch/);assert.throws(()=>continueCampaign(claim,metadata,[]),/cost_mismatch/);continueCampaign(claim,metadata,a);assert.throws(()=>continueCampaign(claim,metadata,a),/not_verified/);}finally{rmSync(d,{recursive:true});}});
