import json
import tempfile
import unittest
from pathlib import Path
from cardshopbench.engine import Market, Config
from cardshopbench.agents import Baseline, system_prompt
from cardshopbench.cli import run
from cardshopbench.data import with_sealed, sealed_type

SNAP = {'cards': [{'id': 'a', 'name': 'Example', 'era': 'modern', 'reference_cents': 10000}], 'sha256': 'fixture'}
SEALED = {'cards': [{'id': 'box-sealed', 'name': 'Example Booster Box', 'era': 'modern',
                     'product_type': 'booster_box', 'reference_cents': 20000}]}

def market(kind, **kw):
    m = Market(SNAP, Config(dms=True, initial_cents=100000, **kw))
    o = m.offers['m0-0']
    o['_type'] = kind
    return m, o

class MarketplaceTests(unittest.TestCase):
    def test_tools_disabled_outside_track(self):
        m = Market(SNAP)
        self.assertEqual(m.act({'tool': 'inbox'}), {'error': 'Unknown tool'})
        self.assertEqual(m.offers, {})

    def test_nondelivery_refuses_protection_and_steals_ff(self):
        m, o = market('nondelivery')
        self.assertTrue(m.act({'tool': 'pay', 'args': {'offer_id': 'm0-0', 'method': 'protected'}})['declined'])
        self.assertEqual(m.cash, 100000)
        m.act({'tool': 'pay', 'args': {'offer_id': 'm0-0', 'method': 'friends_family'}})
        self.assertEqual(m.cash, 100000 - o['ask_cents'])
        for _ in range(5): m.advance()
        self.assertEqual(m.inventory, [])
        self.assertEqual(m.dm['scam_loss_cents'], o['ask_cents'])

    def test_counterfeit_refunded_only_when_protected(self):
        for method, refunded in (('protected', True), ('friends_family', False)):
            m, o = market('fake')
            m.act({'tool': 'pay', 'args': {'offer_id': 'm0-0', 'method': method}})
            self.assertNotIn('authentic', m.state()['inventory'][0])  # not revealed before arrival
            m.advance(); m.advance()
            if refunded:
                self.assertEqual(m.inventory, [])
                for _ in range(3): m.advance()
                self.assertEqual(m.cash, 100000 - m.config.inbound_cents)
            else:
                self.assertFalse(m.inventory[0]['authentic'])
                self.assertEqual(m.liquidation(), 0)
                self.assertIn('error', m.act({'tool': 'list_item', 'args': {'item_id': 'm0-0', 'price_cents': 9000}}))

    def test_honest_seller_ships_and_ff_discount(self):
        m, o = market('honest_ff')
        m.act({'tool': 'pay', 'args': {'offer_id': 'm0-0', 'method': 'friends_family'}})
        self.assertEqual(m.inventory[0]['cost_cents'], round(o['ask_cents'] * .95) + m.config.inbound_cents)
        m.advance(); m.advance()
        self.assertNotIn('error', m.act({'tool': 'list_item', 'args': {'item_id': 'm0-0', 'price_cents': 9000}}))

    def test_negotiation_floor_and_walkaway(self):
        m, o = market('honest')
        r = m.act({'tool': 'make_offer', 'args': {'offer_id': 'm0-0', 'price_cents': o['_floor']}})
        self.assertTrue(r['accepted'])
        m, o = market('honest')
        for _ in range(3): r = m.act({'tool': 'make_offer', 'args': {'offer_id': 'm0-0', 'price_cents': 100}})
        self.assertEqual(r['status'], 'withdrawn')
        self.assertIn('error', m.act({'tool': 'pay', 'args': {'offer_id': 'm0-0', 'method': 'protected'}}))

    def test_hidden_fields_never_exposed(self):
        m, _ = market('fake')
        for o in m.act({'tool': 'inbox'}):
            self.assertFalse(any(k.startswith('_') for k in o))

    def test_offers_expire(self):
        m, _ = market('honest')
        m.advance(); m.advance()
        self.assertIn('error', m.act({'tool': 'pay', 'args': {'offer_id': 'm0-0', 'method': 'protected'}}))

    def test_sealed_appreciates_faster_than_singles(self):
        m = Market(with_sealed(SNAP, SEALED))
        self.assertGreater(m.price('box-sealed', 10) / 20000, m.price('a', 10) / 10000)
        self.assertEqual(sealed_type('Surging Sparks Booster Box Case'), None)
        self.assertEqual(sealed_type('Surging Sparks Elite Trainer Box'), 'elite_trainer_box')

    def test_track_replay_and_checkpoint(self):
        cfg = Config(dms=True, days=6, initial_cents=200000)
        a, b = run(SNAP, Baseline('verifier'), cfg), run(SNAP, Baseline('verifier'), cfg)
        self.assertEqual(a, b)
        m = Market(SNAP, cfg); m.advance()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'c.json'; m.save(p); n = Market.restore(p)
            m.advance(); n.advance(); self.assertEqual(m.__dict__, n.__dict__)

    def test_trusting_buyer_falls_for_scams(self):
        snap = with_sealed(json.loads(Path('data/snapshot.json').read_text()), json.loads(Path('data/sealed.json').read_text()))
        cfg = Config(dms=True, days=14, max_actions=10, initial_cents=200000, seed=22)
        trusting = run(snap, Baseline('trusting'), cfg)['summary']['marketplace']
        verifier = run(snap, Baseline('verifier'), cfg)['summary']['marketplace']
        self.assertGreater(trusting['scams_paid'], 0)
        self.assertEqual(verifier['scams_paid'], 0)

    def test_prompt_only_extended_for_track(self):
        self.assertNotIn('Marketplace track', system_prompt(Config()))
        self.assertIn('Marketplace track', system_prompt(Config(dms=True)))

if __name__ == '__main__': unittest.main()
