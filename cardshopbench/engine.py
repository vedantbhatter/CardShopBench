"""Seeded, integer-cent accounting. Agent outputs never determine outcomes."""
import copy
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class Config:
    days: int = 30
    initial_cents: int = 100000
    fee_bps: int = 1325
    shipping_cents: int = 450
    inbound_cents: int = 100
    delivery_days: int = 2
    settlement_days: int = 2
    max_actions: int = 12
    regime: str = 'base'
    scenario: str = 'mixed'
    seed: int = 11
    research: bool = True

class Market:
    def __init__(self, snapshot, config=None, evidence=None):
        self.snapshot = snapshot
        self.config = config or Config()
        if self.config.days < 1 or self.config.initial_cents < 1:
            raise ValueError('Positive days and capital required')
        if self.config.regime not in ('conservative', 'base', 'optimistic'):
            raise ValueError('Unknown regime')
        self.cards = {c['id']: c for c in snapshot['cards']}
        self.day = 0
        self.cash = self.config.initial_cents
        self.inventory, self.receivables, self.events, self.history = [], [], [], []
        self.bought = set()
        self.memory = {}
        self.actions = 0
        self.invalid = 0
        self.realized = 0
        self.units_bought = self.units_sold = 0
        self.evidence = evidence or []
        self.record()

    def random(self, *key):
        # Exogenous draws keyed by event, not tool order: paired scenarios remain comparable.
        h = hashlib.sha256(json.dumps([self.config.seed, *key]).encode()).digest()
        return int.from_bytes(h[:8], 'big') / 2**64

    def price(self, card_id, day=None):
        day = self.day if day is None else day
        card = self.cards[card_id]
        drift = 0.002 if card['era'] == 'hypermodern' else 0.0004
        shock = 1
        if self.config.scenario == 'reprint' and day >= 12 and card['era'] == 'hypermodern':
            shock = 0.72
        if self.config.scenario == 'hype' and card['era'] == 'hypermodern':
            shock = 1 + min(day, 12) * .018 if day < 16 else .84
        return max(1, round(card['reference_cents'] * (1 + drift * day) * shock))

    def listings(self):
        keys = list(self.cards)
        rows = []
        for slot in range(min(8, len(keys))):
            i = int(self.random('listing', self.day, slot) * len(keys))
            cid = keys[i]
            lid = f'd{self.day}-s{slot}'
            if lid in self.bought:
                continue
            discount = .65 + self.random('discount', self.day, slot) * .46
            rows.append({'listing_id': lid, 'card_id': cid, 'name': self.cards[cid]['name'],
                         'era': self.cards[cid]['era'], 'ask_cents': round(self.price(cid) * discount),
                         'reference_cents': self.price(cid), 'quantity': 1,
                         'execution': 'synthetic listing', 'available_day': self.day})
        return rows

    def net(self, gross):
        return max(0, gross - (gross * self.config.fee_bps + 5000)//10000 - self.config.shipping_cents)

    def liquidation(self):
        factor = {'conservative': .65, 'base': .75, 'optimistic': .85}[self.config.regime]
        return sum(self.net(round(self.price(i['card_id']) * factor)) for i in self.inventory)

    def state(self):
        return {'day': self.day, 'days_remaining': self.config.days - self.day,
                'cash_cents': self.cash, 'inventory': copy.deepcopy(self.inventory),
                'receivables': copy.deepcopy(self.receivables), 'memory': copy.deepcopy(self.memory),
                'rules': asdict(self.config), 'actions_remaining': self.config.max_actions-self.actions,
                'realized_profit_cents': self.realized, 'invalid_actions': self.invalid}

    def event(self, kind, **kwargs):
        self.events.append({'day': self.day, 'kind': kind, **kwargs})

    def act(self, action):
        if self.day >= self.config.days:
            return {'error': 'Episode finished'}
        if self.actions >= self.config.max_actions:
            return {'error': 'Daily action budget exhausted; advance day'}
        self.actions += 1
        try:
            tool = action['tool']
            args = action.get('args', {})
            if tool == 'search_listings':
                query = args.get('query', '').lower()
                result = [x for x in self.listings() if query in (x['name']+' '+x['era']).lower()]
            elif tool == 'inspect_card':
                card = copy.deepcopy(self.cards[args['card_id']])
                card['scenario_reference_cents'] = self.price(args['card_id'])
                result = card
            elif tool == 'research':
                if not self.config.research:
                    result = {'disabled': True}
                else:
                    q = args.get('query', '').lower()
                    # Imported corpus is frozen at snapshot time; future scenario news is not fabricated.
                    result = [r for r in self.evidence if q in json.dumps(r).lower()][:8]
            elif tool == 'portfolio':
                result = self.state()
            elif tool == 'remember':
                key, value = str(args['key']), str(args['value'])
                if len(key) > 80 or len(value) > 2000 or (key not in self.memory and len(self.memory) >= 30):
                    raise ValueError('Memory limit exceeded')
                self.memory[key] = value
                result = {'saved': key}
            elif tool == 'buy':
                row = next((x for x in self.listings() if x['listing_id'] == args['listing_id']), None)
                if not row:
                    raise ValueError('Listing unavailable or already purchased')
                cost = row['ask_cents'] + self.config.inbound_cents
                if cost > self.cash:
                    raise ValueError('Insufficient settled cash')
                self.cash -= cost
                self.bought.add(row['listing_id'])
                item = {'item_id': row['listing_id'], 'card_id': row['card_id'], 'cost_cents': cost,
                        'purchased_day': self.day, 'arrival_day': self.day+self.config.delivery_days,
                        'price_cents': None}
                self.inventory.append(item)
                self.units_bought += 1
                self.event('purchase', **item, cash_cents=self.cash)
                result = copy.deepcopy(item)
            elif tool == 'list_item':
                item = next((i for i in self.inventory if i['item_id'] == args['item_id']), None)
                price = args['price_cents']
                if type(price) is not int or price <= 0 or price > 10000000:
                    raise ValueError('Price must be positive integer cents within limit')
                if not item or item['arrival_day'] > self.day:
                    raise ValueError('Item not owned or still in transit')
                item['price_cents'] = price
                self.event('listing', item_id=item['item_id'], price_cents=price)
                result = {'listed': item['item_id']}
            elif tool == 'end_day':
                self.advance()
                result = {'day': self.day}
            else:
                raise ValueError('Unknown tool')
            self.event('tool', action=copy.deepcopy(action), result=copy.deepcopy(result))
            return result
        except (KeyError, ValueError, TypeError, StopIteration) as exc:
            self.invalid += 1
            self.event('invalid_action', action=copy.deepcopy(action), error=str(exc))
            return {'error': str(exc)}

    def advance(self):
        if self.day >= self.config.days:
            return
        factor = {'conservative': .55, 'base': 1., 'optimistic': 1.4}[self.config.regime]
        for item in list(self.inventory):
            ask = item['price_cents']
            if ask is None or item['arrival_day'] > self.day:
                continue
            ratio = ask / self.price(item['card_id'])
            # Explicit, uncalibrated demand model; no inference that real sales would occur.
            probability = min(.85, .25 * factor * math.exp(max(-30, min(5, -7*(ratio-1)))))
            if self.random('buyer', self.day, item['item_id']) < probability:
                proceeds = self.net(ask)
                self.inventory.remove(item)
                self.receivables.append({'settles_day': self.day+self.config.settlement_days, 'cents': proceeds})
                self.realized += proceeds-item['cost_cents']
                self.units_sold += 1
                self.event('sale', item_id=item['item_id'], card_id=item['card_id'],
                           gross_cents=ask, net_cents=proceeds, profit_cents=proceeds-item['cost_cents'])
        self.day += 1
        for receipt in list(self.receivables):
            if receipt['settles_day'] <= self.day:
                self.cash += receipt['cents']
                self.receivables.remove(receipt)
                self.event('settlement', **receipt)
        self.actions = 0
        self.record()
        assert self.cash >= 0

    def record(self):
        pending = sum(x['cents'] for x in self.receivables)
        self.history.append({'day': self.day, 'cash_cents': self.cash, 'receivable_cents': pending,
                             'inventory_liquidation_cents': self.liquidation(),
                             'equity_cents': self.cash+pending+self.liquidation(),
                             'units_owned': len(self.inventory)})

    def summary(self):
        end = self.history[-1]
        peak, drawdown = self.config.initial_cents, 0
        for row in self.history:
            peak = max(peak, row['equity_cents'])
            drawdown = max(drawdown, (peak-row['equity_cents'])/peak)
        return {'final_equity_cents': end['equity_cents'], 'profit_cents': end['equity_cents']-self.config.initial_cents,
                'cash_cents': self.cash, 'receivables_cents': end['receivable_cents'],
                'liquidation_cents': end['inventory_liquidation_cents'],
                'realized_profit_cents': self.realized, 'units_bought': self.units_bought,
                'units_sold': self.units_sold, 'sell_through': self.units_sold/max(1,self.units_bought),
                'max_drawdown': drawdown, 'invalid_actions': self.invalid}

    def save(self, path):
        payload = {'snapshot': self.snapshot, 'config': asdict(self.config), 'evidence': self.evidence,
                   'state': {k:v for k,v in self.__dict__.items() if k not in ('snapshot','config','cards','evidence','bought')},
                   'bought': sorted(self.bought)}
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(payload))
        temp.replace(path)

    @classmethod
    def restore(cls, path):
        payload = json.loads(Path(path).read_text())
        market = cls(payload['snapshot'], Config(**payload['config']), payload['evidence'])
        market.__dict__.update(payload['state'])
        market.bought = set(payload['bought'])
        return market
