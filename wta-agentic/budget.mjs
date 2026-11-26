import {appendFileSync,existsSync,readFileSync} from 'node:fs';
export class Budget{
 constructor(path,limit=25){if(!Number.isFinite(limit)||limit<=0||limit>25)throw Error('Budget must be positive and <= authorized $25');this.path=path;this.limit=limit;this.entries=existsSync(path)?readFileSync(path,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];this.spent=this.entries.reduce((n,e)=>n+e.delta,0);this.unknown=this.entries.some(e=>e.event==='unknown_retained')||this.entries.some(e=>e.event==='reserve'&&!this.entries.some(s=>s.id===e.id&&s.event==='settle'));}
 record(e){appendFileSync(this.path,JSON.stringify(e)+'\n');this.entries.push(e);this.spent+=e.delta;}
 reserve(id,amount){if(!Number.isFinite(amount)||amount<=0||this.spent+amount>this.limit+1e-9)throw Error('budget_exhausted');if(this.unknown)throw Error('accounting_unknown');this.record({at:new Date().toISOString(),id,event:'reserve',delta:amount,amount});return amount;}
 settle(id,reserved,cost){if(!Number.isFinite(cost)||cost<0){this.unknown=true;this.record({id,event:'unknown_retained',delta:0,reserved});throw Error('accounting_unknown');}this.record({id,event:'settle',delta:cost-reserved,cost,reserved});if(cost>reserved+1e-8){this.unknown=true;throw Error('reservation_exceeded');}}
}
// UTF-8 bytes upper-bound text tokens; large allowance covers schemas/protocol and provider transformations.
export function reservation(body,price){const input=Buffer.byteLength(JSON.stringify(body))+8192;if(input>90000)throw Error('context_cap');const amount=(input*price.prompt+body.max_tokens*price.completion)*1.2;return Math.max(amount,0.001);}
