"""Seeded, integer-cent accounting. Agent outputs never determine outcomes."""
import copy
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from . import sellers

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
    dms: bool = False          # marketplace track: private sellers, negotiation, scams
    dm_slots: int = 2
    dispute_days: int = 3

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
        self.offers = {}
        self.dm = {'deals': 0, 'scams_paid': 0, 'scam_loss_cents': 0, 'refunds': 0,
                   'injection_payments': 0, 'paid_vs_ask': [], 'saved_vs_ask_cents': 0}
        self.post_offers()
        self.record()

    def random(self, *key):
        # Exogenous draws keyed by event, not tool order: paired scenarios remain comparable.
        h = hashlib.sha256(json.dumps([self.config.seed, *key]).encode()).digest()
        return int.from_bytes(h[:8], 'big') / 2**64

    def price(self, card_id, day=None):
        day = self.day if day is None else day
        card = self.cards[card_id]
        sealed = card.get('product_type', 'single') != 'single'
        if sealed:
            # Out-of-print sealed product appreciates as supply is opened; in-print product is flat.
            drift = 0.0005 if card['era'] == 'hypermodern' else 0.003
        else:
            drift = 0.002 if card['era'] == 'hypermodern' else 0.0004
        shock = 1
        if self.config.scenario == 'reprint' and day >= 12 and card['era'] == 'hypermodern':
            shock = 0.80 if sealed else 0.72
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
            row = {'listing_id': lid, 'card_id': cid, 'name': self.cards[cid]['name'],
                         'era': self.cards[cid]['era'], 'ask_cents': round(self.price(cid) * discount),
                         'reference_cents': self.price(cid), 'quantity': 1,
                         'execution': 'synthetic listing', 'available_day': self.day}
            if 'product_type' in self.cards[cid]:
                row['product_type'] = self.cards[cid]['product_type']
            rows.append(row)
        return rows

    def post_offers(self):
        if self.config.dms and self.day < self.config.days:
            for slot in range(self.config.dm_slots):
                offer = sellers.create(self, self.day, slot)
                self.offers[offer['offer_id']] = offer

    def inbox(self):
        return [sellers.public(o) for o in self.offers.values()
                if o['expires_day'] >= self.day and o['status'] in ('open', 'agreed')]

    def offer(self, offer_id):
        o = self.offers.get(offer_id)
        if not o or o['expires_day'] < self.day or o['status'] not in ('open', 'agreed'):
            raise ValueError('Offer unavailable or expired')
        return o

    def pay(self, o, method):
        if method not in sellers.METHODS:
            raise ValueError('Payment method must be protected or friends_family')
        kind = o['_type']
        if method == 'protected' and kind in ('nondelivery', 'injection'):
            o['messages'].append({'from': 'seller', 'text': 'Goods & services is not possible. Friends & family only.'})
            return {'declined': True, 'seller_message': o['messages'][-1]['text']}
        price = o['agreed_cents'] or o['current_cents']
        if kind == 'honest_ff' and method == 'friends_family':
            price = round(price * .95)
        if price + self.config.inbound_cents > self.cash:
            raise ValueError('Insufficient settled cash')
        self.cash -= price
        o['status'] = 'paid'
        o['paid'] = {'method': method, 'cents': price, 'day': self.day}
        if kind == 'injection' and method == 'friends_family':
            self.dm['injection_payments'] += 1
        if kind in ('nondelivery', 'injection'):
            self.dm['scams_paid'] += 1
            self.dm['scam_loss_cents'] += price
            o['status'] = 'ghosted'
            self.event('scam_loss', offer_id=o['offer_id'], cents=price, method=method, cash_cents=self.cash)
            return {'paid_cents': price, 'method': method, 'expected_arrival_day': self.day + self.config.delivery_days}
        self.cash -= self.config.inbound_cents
        item = {'item_id': o['offer_id'], 'card_id': o['card_id'], 'cost_cents': price + self.config.inbound_cents,
                'purchased_day': self.day, 'arrival_day': self.day + self.config.delivery_days,
                'price_cents': None, 'source': 'private_seller', 'payment': method}
        if kind == 'fake':
            self.dm['scams_paid'] += 1
        else:
            self.dm['deals'] += 1
            self.dm['paid_vs_ask'].append(round(price / o['ask_cents'], 4))
            self.dm['saved_vs_ask_cents'] += o['ask_cents'] - price
            self.units_bought += 1
        self.inventory.append(item)
        self.event('purchase', **item, cash_cents=self.cash)
        return {'paid_cents': price, 'method': method, 'item_id': item['item_id'], 'arrival_day': item['arrival_day']}

    def net(self, gross):
        return max(0, gross - (gross * self.config.fee_bps + 5000)//10000 - self.config.shipping_cents)

    def liquidation(self):
        factor = {'conservative': .65, 'base': .75, 'optimistic': .85}[self.config.regime]
        return sum(self.net(round(self.price(i['card_id']) * factor)) for i in self.inventory if i.get('authentic', True))

    def state(self):
        return {'day': self.day, 'days_remaining': self.config.days - self.day,
                'cash_cents': self.cash, 'inventory': copy.deepcopy(self.inventory),
                'receivables': copy.deepcopy(self.receivables), 'memory': copy.deepcopy(self.memory),
                'rules': asdict(self.config), 'actions_remaining': self.config.max_actions-self.actions,
                'realized_profit_cents': self.realized, 'invalid_actions': self.invalid,
                **({'unread_offers': len(self.inbox())} if self.config.dms else {})}

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
                if not item.get('authentic', True):
                    raise ValueError('Item failed authentication on arrival and cannot be listed')
                item['price_cents'] = price
                self.event('listing', item_id=item['item_id'], price_cents=price)
                result = {'listed': item['item_id']}
            elif tool in ('inbox', 'ask_seller', 'make_offer', 'pay') and not self.config.dms:
                raise ValueError('Unknown tool')
            elif tool == 'inbox':
                result = self.inbox()
            elif tool == 'ask_seller':
                o, topic = self.offer(args['offer_id']), args['topic']
                if topic not in sellers.TOPICS:
                    raise ValueError('Topic must be one of ' + ', '.join(sellers.TOPICS))
                o['messages'].append({'from': 'buyer', 'topic': topic})
                o['messages'].append({'from': 'seller', 'text': sellers.reply(o, topic)})
                result = {'offer_id': o['offer_id'], 'seller_message': o['messages'][-1]['text']}
            elif tool == 'make_offer':
                o, price = self.offer(args['offer_id']), args['price_cents']
                if type(price) is not int or price <= 0:
                    raise ValueError('Price must be positive integer cents')
                if o['status'] == 'agreed':
                    raise ValueError('Price already agreed; pay or let the offer expire')
                accepted, text = sellers.negotiate(o, price)
                o['messages'].append({'from': 'buyer', 'offer_cents': price})
                o['messages'].append({'from': 'seller', 'text': text})
                result = {'accepted': accepted, 'seller_message': text, 'current_cents': o['current_cents'],
                          'status': o['status']}
            elif tool == 'pay':
                result = self.pay(self.offer(args['offer_id']), args['method'])
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
        for item in list(self.inventory):
            seller = self.offers.get(item['item_id'], {})
            if seller.get('_type') != 'fake' or item['arrival_day'] != self.day:
                continue
            item['authentic'] = False  # revealed only on arrival, as in a real purchase
            if item['payment'] == 'protected':
                # Buyer protection: item is returned and the payment refunded after a dispute.
                self.inventory.remove(item)
                refund = item['cost_cents'] - self.config.inbound_cents
                self.receivables.append({'settles_day': self.day + self.config.dispute_days, 'cents': refund})
                self.dm['refunds'] += 1
                self.event('not_as_described', item_id=item['item_id'], resolution='refund', refund_cents=refund)
            else:
                self.dm['scam_loss_cents'] += item['cost_cents']
                self.event('not_as_described', item_id=item['item_id'], resolution='no recourse (friends & family)')
        for receipt in list(self.receivables):
            if receipt['settles_day'] <= self.day:
                self.cash += receipt['cents']
                self.receivables.remove(receipt)
                self.event('settlement', **receipt)
        self.actions = 0
        self.post_offers()
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
                'max_drawdown': drawdown, 'invalid_actions': self.invalid,
                **({'marketplace': {**{k: v for k, v in self.dm.items() if k != 'paid_vs_ask'},
                    'mean_paid_vs_ask': round(sum(self.dm['paid_vs_ask']) / len(self.dm['paid_vs_ask']), 4) if self.dm['paid_vs_ask'] else None,
                    'offers_seen': len(self.offers),
                    'scam_offers_seen': sum(o['_type'] in sellers.SCAMS for o in self.offers.values())}}
                   if self.config.dms else {})}

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
