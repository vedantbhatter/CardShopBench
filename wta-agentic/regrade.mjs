import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {scenarios} from './scenarios.mjs';
import {Sandbox} from './sandbox.mjs';
import {grade} from './grade.mjs';
const dir=process.argv[2];if(!dir)throw Error('Specify an existing artifact directory');
const rows=readFileSync(join(dir,'episodes.jsonl'),'utf8').trim().split('\n').filter(Boolean).map(JSON.parse),out=[];
for(const r of rows){const s=scenarios(r.seed).find(x=>x.id===r.scenarioId);if(!s)throw Error('Unknown scenario');const b=new Sandbox(s);for(const e of r.audit){const observed=b.call(e.name,e.args);if(JSON.stringify(observed)!==JSON.stringify(e.out))throw Error('Tool trace mismatch: '+r.scenarioId);}const g=grade(b);out.push({scenarioId:r.scenarioId,model:r.model,repetition:r.repetition,grade:g,unchanged:JSON.stringify(g)===JSON.stringify(r.grade)});}
writeFileSync(join(dir,'regraded.json'),JSON.stringify(out,null,2));console.log(JSON.stringify({episodes:out.length,unchanged:out.every(x=>x.unchanged),accepted:out.filter(x=>x.grade.accepted).length}));
