"""Per-model trading behavior from the published comparison traces.

Usage: python scripts/analyze_traces.py [dist/comparison-traces.zip]
"""
import json
import statistics as st
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cardshopbench.engine import Market, Config

MODELS = {0: 'GPT', 1: 'Claude', 2: 'Gemini', 4: 'Qwen'}

def main():
    root = Path(__file__).resolve().parents[1]
    archive = zipfile.ZipFile(sys.argv[1] if len(sys.argv) > 1 else root / 'dist/comparison-traces.zip')
    snapshot = json.loads((root / 'data/snapshot.json').read_text())
    print('| Model | Bought | Sell-through | Buy / ref | List / ref | Profit per sale | Last buy day | Invalid | remember | research |')
    print('|---|---:|---:|---:|---:|---:|---|---:|---:|---:|')
    for index, name in MODELS.items():
        bought = sold = invalid = remember = research = 0
        buy_ratio, list_ratio, sale_profit, last_buy = [], [], [], []
        for seed in (11, 22):
            run = json.loads(archive.read(f'models/{index}-{seed}.json'))
            market = Market(snapshot, Config(**run['config']))
            events = run['events']
            buys = [e for e in events if e['kind'] == 'purchase']
            cards = {e['item_id']: e['card_id'] for e in buys}
            bought += len(buys)
            sold += sum(e['kind'] == 'sale' for e in events)
            # Ask price relative to the scenario reference on the purchase day (cost includes inbound fee).
            buy_ratio += [(e['cost_cents'] - market.config.inbound_cents) / market.price(e['card_id'], e['purchased_day']) for e in buys]
            list_ratio += [e['price_cents'] / market.price(cards[e['item_id']], e['day']) for e in events if e['kind'] == 'listing']
            sale_profit += [e['profit_cents'] for e in events if e['kind'] == 'sale']
            last_buy.append(str(buys[-1]['day']) if buys else '-')
            invalid += run['summary']['invalid_actions']
            remember += sum(e['kind'] == 'tool' and e['action']['tool'] == 'remember' for e in events)
            research += sum(e['kind'] == 'tool' and e['action']['tool'] == 'research' for e in events)
        print(f"| {name} | {bought} | {sold / bought:.0%} | {st.mean(buy_ratio):.1%} | {st.mean(list_ratio):.1%} | "
              f"${st.mean(sale_profit) / 100:.2f} | {', '.join(last_buy)} | {invalid} | {remember} | {research} |")

if __name__ == '__main__':
    main()
