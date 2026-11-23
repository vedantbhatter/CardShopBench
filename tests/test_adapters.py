import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from cardshopbench.agents import ModelAgent
from cardshopbench.connectors import import_csv
from cardshopbench.engine import Market
from test_engine import SNAP

class FakeResponse:
    def __init__(self,obj): self.obj=obj
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def read(self): return json.dumps(self.obj).encode()

class AdapterTests(unittest.TestCase):
    @patch.dict(os.environ,{'CARDSHOPBENCH_API_KEY':'test-not-a-real-key'})
    def test_model_response_and_usage(self):
        a=ModelAgent('test/model',input_rate=1,output_rate=3)
        payload={'choices':[{'message':{'content':'{"tool":"end_day","args":{}}'}}], 'usage':{'prompt_tokens':100,'completion_tokens':10}}
        with patch('urllib.request.urlopen',return_value=FakeResponse(payload)):
            self.assertEqual(a.step(Market(SNAP))['tool'],'end_day')
        self.assertEqual(a.usage['prompt_tokens'],100)
        self.assertAlmostEqual(a.usage['cost_usd'],.00013)
    @patch.dict(os.environ,{'CARDSHOPBENCH_API_KEY':'test-not-a-real-key'})
    def test_budget_blocks_request(self):
        a=ModelAgent('test/model',input_rate=1,output_rate=3,max_cost=0)
        with patch('urllib.request.urlopen') as call:
            with self.assertRaises(RuntimeError):a.step(Market(SNAP))
            call.assert_not_called()
    @patch.dict(os.environ,{'CARDSHOPBENCH_API_KEY':'test-not-a-real-key'})
    def test_malformed_output_counted(self):
        a=ModelAgent('test/model',input_rate=1,output_rate=3)
        with patch('urllib.request.urlopen',return_value=FakeResponse({'choices':[{'message':{'content':'not json'}}]})):
            market=Market(SNAP); market.act(a.step(market)); self.assertEqual(market.invalid,1)
    def test_import_requires_identity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.csv';p.write_text('source,source_url,observed_at,card_id,name,variant,condition,price_cents,observation_kind\neBay,https://example.org/item,2026-11-23T00:00:00Z,,Pikachu,Normal,NM,1000,asking_price\n')
            with self.assertRaises(ValueError):import_csv(p)
    def test_research_ablation(self):
        from cardshopbench.engine import Config
        m=Market(SNAP,Config(research=False),[{'content':'vintage'}])
        self.assertEqual(m.act({'tool':'research','args':{'query':'vintage'}}),{'disabled':True})
