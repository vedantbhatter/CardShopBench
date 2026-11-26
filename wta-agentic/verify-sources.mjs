import {readFileSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {hash} from './sandbox.mjs';
const dir=process.argv[2];if(!dir)throw Error('Specify run directory');const manifest=JSON.parse(readFileSync(join(dir,'manifest.json'),'utf8'));const rows=Object.entries(manifest.sourceHashes??{}).map(([name,expected])=>({name,status:!existsSync(join(dir,'source',name))?'missing':hash(readFileSync(join(dir,'source',name),'utf8'))===expected?'match':'mismatch'}));console.log(JSON.stringify({files:rows.length,verified:rows.filter(r=>r.status==='match').length,problems:rows.filter(r=>r.status!=='match')},null,2));if(rows.some(r=>r.status!=='match'))process.exitCode=1;
