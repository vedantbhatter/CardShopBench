import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {scenarios} from './scenarios.mjs';
import {contractScenarios} from './contract-v2.mjs';
import {Sandbox,hash} from './sandbox.mjs';
import {grade,GRADER_VERSION} from './grade.mjs';
const dir=process.argv[2];if(!dir)throw Error('Specify an existing artifact directory');
const lines=name=>readFileSync(join(dir,name),'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const rows=lines('episodes.jsonl'),attempts=existsSync(join(dir,'attempts-final.json'))?JSON.parse(readFileSync(join(dir,'attempts-final.json'),'utf8')):lines('attempts.jsonl');
// Native inference is serial. Every business episode starts at step 0; smoke has no scenarioId.
const groups=[];for(const a of attempts.filter(a=>a.scenarioId)){if(a.step===0||!groups.length)groups.push([]);groups.at(-1).push(a);}
let groupIndex=0;const corrected=[],reviews=[];
for(const r of rows){const s=[...scenarios(r.seed),...contractScenarios(r.seed)].find(x=>x.id===r.scenarioId);if(!s)throw Error('Unknown scenario '+r.scenarioId);const b=new Sandbox(s);for(const e of r.audit){const observed=b.call(e.name,e.args);if(hash(observed)!==hash(e.out))throw Error('Tool trace mismatch: '+r.scenarioId+' '+e.name);}const g=grade(b);let group=groups[groupIndex]??[];if(group[0]?.scenarioId!==r.scenarioId||group[0]?.requestedModel!==r.model){if(r.calls>0||r.trace.length)throw Error('Attempt assignment mismatch '+r.scenarioId);group=[];}else groupIndex++;
 const billed=group.reduce((n,a)=>n+(a.cost??0),0),unknown=group.filter(a=>a.cost===null).reduce((n,a)=>n+a.reserved,0),pending=group.filter(a=>a.pendingGeneration).reduce((n,a)=>n+Math.max(0,a.reserved-a.cost),0);
 corrected.push({...r,experiment:r.experiment??'baseline-v1',originalGrade:r.originalGrade??r.grade,grade:g,graderVersion:GRADER_VERSION,accountingLedgerDelta:r.accountingLedgerDelta??r.cost,cost:billed,unknownReserved:unknown,pendingReserved:pending,conservativeCost:billed+unknown+pending,attemptIds:group.map(a=>a.id)});
 reviews.push({scenarioId:r.scenarioId,model:r.model,repetition:r.repetition,originalAccepted:r.grade.accepted,accepted:g.accepted,changed:hash(g)!==hash(r.grade)});
 for(const a of group){a.repetition=r.repetition;a.experiment=r.experiment??'baseline-v1';}
}
if(groupIndex!==groups.length)throw Error('Unassigned business attempts remain');
writeFileSync(join(dir,'episodes-corrected.jsonl'),corrected.map(r=>JSON.stringify(r)).join('\n')+'\n');writeFileSync(join(dir,'attempts-corrected.json'),JSON.stringify(attempts,null,2));writeFileSync(join(dir,'regraded.json'),JSON.stringify({graderVersion:GRADER_VERSION,episodes:reviews},null,2));console.log(JSON.stringify({episodes:reviews.length,accepted:reviews.filter(x=>x.accepted).length,changedAcceptance:reviews.filter(x=>x.originalAccepted!==x.accepted).length,allToolTracesReplayed:true}));
