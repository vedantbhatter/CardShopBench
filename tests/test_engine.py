import json
import tempfile
import unittest
from pathlib import Path
from cardshopbench.engine import Market, Config
from cardshopbench.agents import Baseline
from cardshopbench.cli import run
from cardshopbench.data import evidence_before

SNAP={'cards':[{'id':'a','name':'Example','era':'modern','reference_cents':10000}], 'sha256':'fixture'}
class EngineTests(unittest.TestCase):
    def test_no_double_purchase(self):
        m=Market(SNAP); lid=m.listings()[0]['listing_id']
        m.act({'tool':'buy','args':{'listing_id':lid}}); cash=m.cash
        self.assertIn('error',m.act({'tool':'buy','args':{'listing_id':lid}})); self.assertEqual(m.cash,cash)
    def test_cannot_overspend(self):
        m=Market(SNAP,Config(initial_cents=1)); self.assertIn('error',m.act({'tool':'buy','args':{'listing_id':m.listings()[0]['listing_id']}})); self.assertEqual(m.cash,1)
    def test_transit_and_price_validation(self):
        m=Market(SNAP); lid=m.listings()[0]['listing_id']; m.act({'tool':'buy','args':{'listing_id':lid}})
        for p in (10000,-1,True): self.assertIn('error',m.act({'tool':'list_item','args':{'item_id':lid,'price_cents':p}}))
        m.advance(); m.advance(); self.assertNotIn('error',m.act({'tool':'list_item','args':{'item_id':lid,'price_cents':10000}}))
    def test_deterministic_replay(self):
        a=run(SNAP,Baseline('margin'),Config()); b=run(SNAP,Baseline('margin'),Config()); self.assertEqual(a,b)
    def test_exogenous_draws_ignore_tool_order(self):
        a,b=Market(SNAP),Market(SNAP); a.act({'tool':'portfolio'}); self.assertEqual(a.listings(),b.listings()); self.assertEqual(a.random('buyer',4,'x'),b.random('buyer',4,'x'))
    def test_checkpoint_equivalence(self):
        m=Market(SNAP); m.act({'tool':'buy','args':{'listing_id':m.listings()[0]['listing_id']}}); m.advance()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'checkpoint.json'; m.save(p); n=Market.restore(p)
            m.advance(); n.advance(); self.assertEqual(m.__dict__,n.__dict__)
    def test_cash_baseline(self):
        r=run(SNAP,Baseline('cash'),Config()); self.assertEqual(r['summary']['profit_cents'],0)
    def test_temporal_gate(self):
        rows=[{'published_at':'2026-01-01T00:00:00Z','observed_at':'2026-01-03T00:00:00Z'}]
        self.assertEqual(evidence_before(rows,'2026-01-02T00:00:00Z'),[])
        self.assertEqual(len(evidence_before(rows,'2026-01-03T00:00:00Z')),1)
    def test_settlement_not_immediate(self):
        m=Market(SNAP,Config(delivery_days=0)); lid=m.listings()[0]['listing_id']; m.act({'tool':'buy','args':{'listing_id':lid}})
        m.act({'tool':'list_item','args':{'item_id':lid,'price_cents':10000}}); cash=m.cash
        m.random=lambda *a:0; m.advance(); self.assertEqual(m.cash,cash); self.assertTrue(m.receivables)
        m.advance(); self.assertGreater(m.cash,cash); self.assertFalse(m.receivables)
    def test_cash_conservation(self):
        r=run(SNAP,Baseline('margin'),Config())
        buys=sum(e['cost_cents'] for e in r['events'] if e['kind']=='purchase')
        sales=sum(e['net_cents'] for e in r['events'] if e['kind']=='sale')
        self.assertEqual(r['summary']['cash_cents']+r['summary']['receivables_cents'],100000-buys+sales)
    def test_terminal_guard(self):
        m=Market(SNAP,Config(days=1)); m.advance(); h=len(m.history); m.advance(); self.assertEqual(len(m.history),h); self.assertIn('error',m.act({'tool':'buy'}))
    def test_action_limit(self):
        m=Market(SNAP,Config(max_actions=1)); m.act({'tool':'portfolio'}); self.assertIn('error',m.act({'tool':'portfolio'}))
if __name__=='__main__': unittest.main()
