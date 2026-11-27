'use strict';
const $ = s => document.querySelector(s);
const names = {margin: 'Margin buyer', momentum: 'Hype chaser', cash: 'Cash hold'};
const color = k => getComputedStyle(document.documentElement).getPropertyValue('--' + k).trim();
const money = c => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 0}).format(c / 100);
const precise = c => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(c / 100);
let data;

function render() {
  const scenario = $('#scenario').value, regime = $('#regime').value;
  const runs = data.runs.filter(r => r.config.scenario === scenario && r.config.regime === regime);
  const rows = data.aggregates
    .filter(r => r.scenario === scenario && r.regime === regime)
    .sort((a, b) => b.mean_profit_cents - a.mean_profit_cents);

  $('#leaderboard').innerHTML = rows.map(r => `<tr>
    <td>${names[r.agent]}</td>
    <td class="${r.mean_profit_cents >= 0 ? 'positive' : 'negative'}">${precise(r.mean_profit_cents)}</td>
    <td>${money(r.bootstrap_ci_cents[0])} to ${money(r.bootstrap_ci_cents[1])}</td>
    <td>${(r.mean_sell_through * 100).toFixed(1)}%</td>
    <td>${(r.mean_drawdown * 100).toFixed(1)}%</td></tr>`).join('');

  const days = runs[0].history.length - 1;
  const series = Object.keys(names).map(agent => {
    const rr = runs.filter(r => r.agent === agent);
    return {agent, values: Array.from({length: days + 1}, (_, d) => rr.reduce((t, r) => t + r.history[d].equity_cents, 0) / rr.length)};
  });
  const all = series.flatMap(s => s.values);
  const low = Math.floor((Math.min(...all) - 5000) / 10000) * 10000;
  const high = Math.ceil((Math.max(...all) + 5000) / 10000) * 10000;
  const W = 720, H = 300, L = 64, R = 12, T = 10, B = 30;
  const x = d => L + d / days * (W - L - R), y = v => H - B - (v - low) / (high - low) * (H - T - B);
  const muted = color('muted'), line = color('line');
  let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">`;
  for (let i = 0; i <= 4; i++) {
    const v = low + (high - low) * i / 4;
    svg += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="${line}"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" fill="${muted}" font-size="12">${money(v)}</text>`;
  }
  for (let d = 0; d <= days; d += 5) svg += `<text x="${x(d)}" y="${H - 8}" text-anchor="middle" fill="${muted}" font-size="12">${d === 0 ? 'Day 0' : d}</text>`;
  for (const s of series) {
    svg += `<polyline fill="none" stroke="${color(s.agent)}" stroke-width="2.5" ${s.agent === 'cash' ? 'stroke-dasharray="5 5"' : ''} points="${s.values.map((v, d) => `${x(d)},${y(v)}`).join(' ')}"/>`;
  }
  $('#chart').innerHTML = svg + '</svg>';
}

fetch('results.json')
  .then(r => { if (!r.ok) throw Error('results.json unavailable'); return r.json(); })
  .then(d => { data = d; render(); })
  .catch(e => { $('#chart').textContent = 'Could not load results. Serve this folder over HTTP.'; console.error(e); });
$('#scenario').addEventListener('change', render);
$('#regime').addEventListener('change', render);

// Agent loop animation: an illustrative episode run through the real fee and delay rules.
(function loopDemo() {
  const root = $('#loop-demo');
  if (!root) return;
  const usd = c => '$' + (c / 100).toLocaleString('en-US', {minimumFractionDigits: 2});
  const steps = [
    {tool: 'search_listings', args: {query: 'umbreon'}, why: 'Look for underpriced Umbreon listings.',
     result: '[{"listing_id":"d0-s3","name":"Umbreon V (Alternate Full Art)","ask_cents":26800,"reference_cents":37503}]'},
    {tool: 'buy', args: {listing_id: 'd0-s3'}, why: 'Ask is 71% of reference; margin clears fees.',
     apply: s => { s.cash -= 26900; s.inv = 1; s.events.push('purchase d0-s3'); }, flash: ['l-cash', 'l-inv'],
     result: '{"item_id":"d0-s3","cost_cents":26900,"arrival_day":2}'},
    {tool: 'list_item', args: {item_id: 'd0-s3', price_cents: 36900}, why: 'List just under reference.',
     error: 'Item not owned or still in transit', apply: s => { s.bad += 1; s.events.push('invalid_action'); }, flash: ['l-bad']},
    {tool: 'remember', args: {key: 'plan', value: 'List d0-s3 at $369 once it arrives (day 2).'}, why: 'Save the plan for later steps.',
     apply: s => { s.memory = {plan: 'List d0-s3 at $369 once it arrives (day 2).'}; }, result: '{"saved":"plan"}'},
    {tool: 'end_day', args: {}, why: 'Nothing else to do until delivery.',
     apply: s => { s.day = 1; s.events.push('day 1'); }, flash: ['l-day'], result: '{"day":1}'},
    {tool: 'end_day', args: {}, why: 'Still in transit.',
     apply: s => { s.day = 2; s.events.push('day 2'); }, flash: ['l-day'], result: '{"day":2}'},
    {tool: 'list_item', args: {item_id: 'd0-s3', price_cents: 36900}, why: 'Card has arrived; follow the saved plan.',
     apply: s => { s.events.push('listing d0-s3'); }, result: '{"listed":"d0-s3"}'},
    {tool: 'end_day', args: {}, why: 'Let buyers see the listing.',
     apply: s => { s.day = 3; s.inv = 0; s.pend = 31561; s.events.push('sale d0-s3'); }, flash: ['l-day', 'l-inv', 'l-pend'],
     result: '{"day":3}  // sold for $369.00: −$48.89 fee, −$4.50 shipping → $315.61 net, settles day 4'}
  ];
  const phases = ['Observe', 'Decide', 'Validate', 'Execute'];
  const fresh = () => ({day: 0, cash: 100000, pend: 0, inv: 0, bad: 0, memory: {}, events: []});
  let state = fresh(), step = 0, phase = 0, timer = null, playing = true, touched = false;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const esc = s => String(s).replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));

  function ledger(flash = []) {
    $('#l-day').textContent = state.day;
    $('#l-cash').textContent = usd(state.cash);
    $('#l-pend').textContent = usd(state.pend);
    $('#l-inv').textContent = state.inv;
    $('#l-bad').textContent = state.bad;
    for (const id of flash) { const el = document.getElementById(id); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 900); }
  }
  function on(ids) {
    root.querySelectorAll('.on').forEach(el => el.classList.remove('on'));
    for (const id of ids) document.getElementById(id).classList.add('on');
  }
  function travel(pathId) {
    const path = document.getElementById(pathId), dot = $('#packet'), len = path.getTotalLength();
    if (reduce) { dot.setAttribute('opacity', 0); return; }
    const t0 = performance.now(), dur = 700;
    dot.setAttribute('opacity', 1);
    (function frame(now) {
      const t = Math.min(1, (now - t0) / dur), p = path.getPointAtLength(len * (1 - Math.pow(1 - t, 2)));
      dot.setAttribute('cx', p.x); dot.setAttribute('cy', p.y);
      if (t < 1) requestAnimationFrame(frame); else dot.setAttribute('opacity', 0);
    })(t0);
  }
  function render() {
    const s = steps[step], model = $('#n-model'), val = $('#n-val');
    $('#loop-step').textContent = `Step ${step + 1} of ${steps.length}`;
    $('#loop-phase').textContent = phases[phase];
    model.classList.remove('thinking');
    if (phase === 0) {
      val.classList.remove('ok', 'bad'); $('#v-text').textContent = 'validate';
      $('#m-tool').textContent = '—'; $('#m-note').textContent = 'reading state';
      on(['n-env', 'p-obs']); travel('p-obs');
      const obs = {day: state.day, cash_cents: state.cash, pending_cents: state.pend, inventory: state.inv,
        actions_remaining: [6, 5, 4, 3, 2, 6, 6, 5][step], memory: state.memory,
        recent_events: state.events.slice(-3)};
      $('#loop-code').innerHTML = esc(JSON.stringify(obs));
    } else if (phase === 1) {
      on(['n-model']); model.classList.add('thinking');
      $('#m-tool').textContent = s.tool + '()'; $('#m-note').textContent = 'returns one JSON action';
      $('#loop-code').innerHTML = esc(JSON.stringify({tool: s.tool, args: s.args, rationale: s.why}));
    } else if (phase === 2) {
      on(['n-val', 'p-act']); travel('p-act');
      val.classList.add(s.error ? 'bad' : 'ok'); $('#v-text').textContent = s.error ? '✗ rejected' : '✓ valid';
      $('#loop-code').innerHTML = s.error
        ? `<span class="err">✗ ${esc(s.error)}</span>\nThe action still uses one of the day's 6 actions and is logged as invalid.`
        : `<span class="ok">✓ valid JSON · known tool · arguments type-checked</span>`;
    } else {
      on(['n-env', 'p-exec']); travel('p-exec');
      if (s.apply) s.apply(state);
      ledger(s.flash || []);
      $('#loop-code').innerHTML = s.error ? `<span class="err">{"error":"${esc(s.error)}"}</span>  // returned to the model next step` : esc(s.result);
    }
  }
  function advance() {
    phase++;
    if (phase > 3) { phase = 0; step++; }
    if (step >= steps.length) { step = 0; state = fresh(); ledger(); }
    render();
  }
  function play(v) {
    playing = v; $('#loop-play').textContent = v ? 'Pause' : 'Play';
    clearInterval(timer); timer = v ? setInterval(advance, 1500) : null;
  }
  $('#loop-play').addEventListener('click', () => { touched = true; play(!playing); });
  $('#loop-next').addEventListener('click', () => { touched = true; play(false); advance(); });
  ledger(); render();
  // Start when scrolled into view so the reader sees step 1.
  if (reduce) { play(false); return; }
  play(false);
  new IntersectionObserver((entries, obs) => { if (entries[0].isIntersecting) { if (!touched) play(true); obs.disconnect(); } }, {threshold: .4}).observe(root);
})();
