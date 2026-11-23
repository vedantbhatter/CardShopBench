"""Public pricing snapshot collector and timestamp-gated evidence loader."""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://tcgcsv.com/tcgplayer/3'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'CardShopBench/0.1 research snapshot'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def collect(group_ids, output, per_group=25):
    groups = {g['groupId']: g for g in fetch(BASE + '/groups')['results']}
    now = datetime.now(timezone.utc).isoformat()
    cards, sources = [], []
    for gid in group_ids:
        group = groups[gid]
        if group.get('publishedOn', '')[:10] > now[:10]:
            raise ValueError('Unreleased groups are excluded')
        purl, vurl = f'{BASE}/{gid}/products', f'{BASE}/{gid}/prices'
        products = {p['productId']: p for p in fetch(purl)['results']}
        prices = fetch(vurl)['results']
        candidates = []
        for price in prices:
            product = products.get(price['productId'])
            if not product or not price.get('marketPrice'):
                continue
            extra = {x['name']: x['value'] for x in product.get('extendedData', [])}
            if not extra.get('Number') or not 5 <= price['marketPrice'] <= 500:
                continue
            year = int(group.get('publishedOn', '2020')[:4])
            era = 'vintage' if year <= 2003 else 'hypermodern' if year >= 2023 else 'modern'
            candidates.append({'id': f"{product['productId']}-{price.get('subTypeName','Normal')}",
                'name': product['name'], 'set': group['name'], 'number': extra.get('Number'),
                'variant': price.get('subTypeName'), 'era': era,
                'reference_cents': round(price['marketPrice'] * 100),
                'condition': 'unspecified aggregate', 'grading_company': None, 'grade': None,
                'source_url': product.get('url', purl), 'image_url': product.get('imageUrl'),
                'observed_at': now, 'source': 'TCGCSV / TCGplayer-derived',
                'observation_kind': 'aggregate_market_reference',
                'liquidity': None, 'population': None})
        candidates.sort(key=lambda c: c['reference_cents'], reverse=True)
        cards.extend(candidates[:per_group])
        sources.extend([purl, vurl])
    if not cards:
        raise ValueError('No eligible cards found')
    result = {'schema_version': 1, 'observed_at': now, 'mode': 'real_snapshot',
              'sources': sources, 'limitations': ['Aggregate references, not executable asks or individual sold records.',
              'No condition-level prices, empirical liquidity, population data, or historical price path.',
              'All scenario listing discounts, future price movement and buyer demand are synthetic.'], 'cards': cards}
    result['sha256'] = hashlib.sha256(json.dumps(cards, sort_keys=True).encode()).hexdigest()
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, indent=2))
    return result

def load_snapshot(path):
    data = json.loads(Path(path).read_text())
    if not data.get('cards'):
        raise ValueError('Empty snapshot')
    for c in data['cards']:
        if not isinstance(c['reference_cents'], int) or c['reference_cents'] <= 0:
            raise ValueError('Prices must be positive integer cents')
    return data

def evidence_before(records, as_of):
    cutoff = datetime.fromisoformat(as_of.replace('Z', '+00:00'))
    if cutoff.tzinfo is None:
        raise ValueError('Timezone required')
    return [r for r in records if max(datetime.fromisoformat(r[k].replace('Z', '+00:00'))
            for k in ('published_at', 'observed_at')) <= cutoff]
