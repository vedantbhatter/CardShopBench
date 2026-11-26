"""Summarize marketplace-track runs: scam handling, negotiation, and sealed product.

Usage: python scripts/analyze_marketplace.py RUN_DIR [RUN_DIR ...]
Each RUN_DIR holds pilot outputs named <model>-<seed>.json (and optional baseline-*.json).
"""
import json
import statistics as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cardshopbench.data import load_snapshot, with_sealed

def kinds(root):
    snap = with_sealed(load_snapshot(root / 'data/snapshot.json'), load_snapshot(root / 'data/sealed.json'))
    return {c['id']: c.get('product_type', 'single') for c in snap['cards']}

def episode(run, product_kind):
    events = run['events']
    tools = [e['action'] for e in events if e['kind'] in ('tool', 'invalid_action')]
    mk = run['summary']['marketplace']
    asked = sum(a.get('tool') == 'ask_seller' for a in tools)
    bids = sum(a.get('tool') == 'make_offer' for a in tools)
    pays = [a for a in tools if a.get('tool') == 'pay']
    return {
        'profit': run['summary']['profit_cents'], 'deals': mk['deals'], 'scams_paid': mk['scams_paid'],
        'scam_loss': mk['scam_loss_cents'], 'refunds': mk['refunds'], 'injection': mk['injection_payments'],
        'scams_seen': mk['scam_offers_seen'], 'asked': asked, 'bids': bids,
        'pays_protected': sum(p.get('args', {}).get('method') == 'protected' for p in pays),
        'pays_ff': sum(p.get('args', {}).get('method') == 'friends_family' for p in pays),
        'declined': sum(e['kind'] == 'tool' and isinstance(e.get('result'), dict) and bool(e['result'].get('declined')) for e in events),
        'paid_vs_ask': mk['mean_paid_vs_ask'],
        'sealed_bought': sum(e['kind'] == 'purchase' and product_kind.get(e['card_id'], 'single') != 'single' for e in events),
        'bought': sum(e['kind'] == 'purchase' for e in events), 'invalid': run['summary']['invalid_actions'],
        'cost': run.get('reported_api_cost_usd', 0) or 0, 'status': run['status'],
    }

def main():
    root = Path(__file__).resolve().parents[1]
    product_kind = kinds(root)
    rows = {}
    for d in map(Path, sys.argv[1:]):
        for f in sorted(d.glob('*.json')):
            run = json.loads(f.read_text())
            if 'summary' not in run or 'marketplace' not in run['summary']:
                continue
            rows.setdefault(run['agent'], []).append(episode(run, product_kind))
    cols = ['profit', 'deals', 'scams_paid', 'scam_loss', 'refunds', 'injection', 'asked', 'bids', 'pays_protected',
            'pays_ff', 'declined', 'sealed_bought', 'bought', 'invalid', 'cost']
    print('| Agent | n | ' + ' | '.join(cols) + ' | paid/ask |')
    print('|---' * (len(cols) + 3) + '|')
    for agent, eps in rows.items():
        sums = {c: sum(e[c] for e in eps) for c in cols}
        sums['profit'] = f"{st.mean(e['profit'] for e in eps) / 100:.2f} (mean)"
        sums['scam_loss'] = f"{sums['scam_loss'] / 100:.2f}"
        sums['cost'] = f"{sums['cost']:.2f}"
        ratios = [e['paid_vs_ask'] for e in eps if e['paid_vs_ask']]
        status = ','.join(e['status'] for e in eps)
        paid = f'{st.mean(ratios):.3f}' if ratios else '-'
        print(f"| {agent} | {len(eps)} ({status}) | " + ' | '.join(str(sums[c]) for c in cols) + f' | {paid} |')

if __name__ == '__main__':
    main()
