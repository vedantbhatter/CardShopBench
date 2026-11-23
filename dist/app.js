'use strict';
const $=s=>document.querySelector(s), names={margin:'Margin buyer',momentum:'Hype chaser',cash:'Cash hold'},colors={margin:'#327252',momentum:'#c47842',cash:'#98a59e'};
const money=c=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(c/100);
const precise=c=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(c/100);
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data,visible=12,timer;
function selection(){return {scenario:$('#scenario').value,regime:$('#regime').value};}
function selectedRuns(){const s=selection();return data.runs.filter(r=>r.config.scenario===s.scenario&&r.config.regime===s.regime);}
function renderResults(){
 const runs=selectedRuns(),s=selection();
 const rows=data.aggregates.filter(r=>r.scenario===s.scenario&&r.regime===s.regime).sort((a,b)=>b.mean_profit_cents-a.mean_profit_cents);
 $('#leaderboard').innerHTML=rows.map(r=>`<tr><td><i style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${colors[r.agent]};margin-right:9px"></i>${names[r.agent]}</td><td class="${r.mean_profit_cents>=0?'positive':'negative'}">${precise(r.mean_profit_cents)}</td><td>${money(r.bootstrap_ci_cents[0])} to ${money(r.bootstrap_ci_cents[1])}</td><td>${(r.mean_sell_through*100).toFixed(1)}%</td><td>${(r.mean_drawdown*100).toFixed(1)}%</td></tr>`).join('');
 const series=Object.keys(names).map(agent=>({agent,values:Array.from({length:31},(_,day)=>{const rr=runs.filter(r=>r.agent===agent);return rr.reduce((t,r)=>t+r.history[day].equity_cents,0)/rr.length;})}));
 const all=series.flatMap(s=>s.values),low=Math.floor((Math.min(...all)-5000)/10000)*10000,high=Math.ceil((Math.max(...all)+5000)/10000)*10000;
 const x=d=>72+d/30*950,y=v=>270-(v-low)/(high-low)*235;
 let svg=`<svg viewBox="0 0 1060 315" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mean equity trajectories for three baseline strategies"><title>Mean business equity across five paired seeds</title>`;
 for(let i=0;i<5;i++){const value=low+(high-low)*i/4,py=y(value);svg+=`<line x1="72" y1="${py}" x2="1022" y2="${py}" stroke="#e8ede5"/><text x="60" y="${py+4}" text-anchor="end" fill="#6c7a70" font-size="12">${money(value)}</text>`;}
 for(let d=0;d<=30;d+=5)svg+=`<text x="${x(d)}" y="298" text-anchor="middle" fill="#6c7a70" font-size="12">${d===0?'Day 0':d}</text>`;
 for(const line of series){svg+=`<polyline points="${line.values.map((v,d)=>`${x(d)},${y(v)}`).join(' ')}" fill="none" stroke="${colors[line.agent]}" stroke-width="${line.agent==='cash'?2:3}" ${line.agent==='cash'?'stroke-dasharray="5 5"':''}/>`;svg+=`<circle cx="${x(30)}" cy="${y(line.values[30])}" r="4" fill="${colors[line.agent]}"/>`;}
 $('#chart').innerHTML=svg+'</svg>';
 const best=rows[0];$('#finding').innerHTML=`<strong>What this run configuration shows</strong>${names[best.agent]} ends with the highest mean equity under ${escape(s.regime)} execution assumptions: ${precise(100000+best.mean_profit_cents)}. Change the scenario or execution regime to see whether the comparison holds. This is a simulator finding, not evidence of real-world returns.`;
 renderReplay();
}
function renderReplay(){
 const run=selectedRuns().find(r=>r.agent===$('#replay-agent').value&&r.config.seed===Number($('#seed').value));
 const day=Number($('#day').value),row=run.history[day];$('#day-label').textContent=day;$('#equity').textContent=precise(row.equity_cents);
 $('#ledger-rows').innerHTML=[['Settled cash',precise(row.cash_cents)],['Pending settlements',precise(row.receivable_cents)],['Inventory liquidation',precise(row.inventory_liquidation_cents)],['Cards in inventory',row.units_owned]].map(([a,b])=>`<div class="ledger-row"><span>${a}</span><b>${b}</b></div>`).join('');
 // Day N balance is the start of day N. Show only earlier actions and day-N settlement events.
 const events=run.events.filter(e=>(e.day<day||(e.day===day&&e.kind==='settlement'))&&['purchase','sale','listing','invalid_action','forced_advance','settlement'].includes(e.kind));
 $('#event-count').textContent=`${events.length} events through day ${day}`;
 $('#events').innerHTML=events.length?events.slice().reverse().map(e=>{const card=data.snapshot.cards.find(c=>c.id===e.card_id);let title='',detail='';
 if(e.kind==='purchase'){title=`Bought ${card?.name||e.card_id}`;detail=`${precise(e.cost_cents)} landed cost · arrives day ${e.arrival_day}`;}
 if(e.kind==='sale'){title=`Sold ${card?.name||e.card_id}`;detail=`${precise(e.gross_cents)} gross · ${precise(e.net_cents)} net · ${precise(e.profit_cents)} realized margin`;}
 if(e.kind==='listing'){title=`Listed inventory ${e.item_id}`;detail=`Asking ${precise(e.price_cents)}`;}
 if(e.kind==='settlement'){title='Sale proceeds settled';detail=`${precise(e.cents)} available to spend`;}
 if(e.kind==='invalid_action'){title='Action rejected';detail=e.error;}
 if(e.kind==='forced_advance'){title='Daily action limit reached';detail=e.reason;}
 return `<div class="event"><span class="event-tag">D${e.day} / ${e.kind==='purchase'?'BUY':escape(e.kind.toUpperCase())}</span><div>${escape(title)}<p>${escape(detail)}</p></div></div>`;}).join(''):'<p class="empty">No transactions yet. Advance the day to follow this strategy.</p>';
}
function renderCards(){const q=$('#card-search').value.toLowerCase(),cards=data.snapshot.cards.filter(c=>(c.name+' '+c.set+' '+c.era).toLowerCase().includes(q));$('#cards').innerHTML=cards.slice(0,visible).map(c=>`<a class="market-card" href="${escape(c.source_url)}" target="_blank" rel="noopener"><img src="${escape(c.image_url||'icon.svg')}" alt="${escape(c.name)}" loading="lazy"><h3>${escape(c.name)}</h3><p>${escape(c.set)} · ${escape(c.variant)}</p><strong>${precise(c.reference_cents)}</strong><small>Aggregate reference · ${escape(c.era)}</small></a>`).join('')||'<p>No matching cards.</p>';$('#more-cards').hidden=visible>=cards.length;}
async function init(){try{const res=await fetch('results.json');if(!res.ok)throw Error('Results unavailable');data=await res.json();$('#card-count').textContent=data.snapshot.cards.length;$('#run-count').textContent=data.runs.length;$('#snapshot-date').textContent='Snapshot observed '+new Date(data.snapshot.observed_at).toLocaleDateString('en-US',{year:'numeric',month:'short',day:'numeric',timeZone:'UTC'});const hero=data.snapshot.cards.find(c=>c.name.includes('Pikachu'))||data.snapshot.cards[0];$('#hero-card-image').innerHTML=`<img src="${escape(hero.image_url)}" alt="${escape(hero.name)}">`;renderResults();renderCards();}catch(e){$('#chart').textContent='Could not load experiment data. Serve this site over HTTP or reload the page.';console.error(e);}}
for(const id of ['scenario','regime'])$('#'+id).addEventListener('change',()=>{renderResults();});
for(const id of ['replay-agent','seed'])$('#'+id).addEventListener('change',renderReplay);
$('#day').addEventListener('input',renderReplay);
$('#play').addEventListener('click',()=>{if(timer){clearInterval(timer);timer=null;$('#play').textContent='Play replay';return;}if(Number($('#day').value)>=30)$('#day').value=0;$('#play').textContent='Pause replay';timer=setInterval(()=>{$('#day').value=Number($('#day').value)+1;renderReplay();if(Number($('#day').value)>=30){clearInterval(timer);timer=null;$('#play').textContent='Play replay';}},600);});
$('#card-search').addEventListener('input',()=>{visible=12;renderCards();});$('#more-cards').addEventListener('click',()=>{visible+=12;renderCards();});
$('#copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('#quickstart').textContent);$('#copy').textContent='Copied';}catch{$('#copy').textContent='Select text to copy';}});
init();
