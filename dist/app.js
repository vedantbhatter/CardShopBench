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
