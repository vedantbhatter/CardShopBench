import sys,unittest,io,urllib.error
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rate_limits import request_json,retry_delay
class RateLimitTests(unittest.TestCase):
 def agent(self):return SimpleNamespace(usage={'cost_usd':0},max_cost=1,calls=0,retry_events=[])
 def test_429_then_success(self):
  a=self.agent();err=urllib.error.HTTPError('https://example.test',429,'rate',{'Retry-After':'2'},None)
  with patch('rate_limits.time.sleep'),patch('rate_limits.urllib.request.urlopen',side_effect=[err,io.BytesIO(b'{"ok":true}')]):
   self.assertTrue(request_json(a,None,.1,0)['ok'])
  self.assertEqual(a.calls,2);self.assertAlmostEqual(a.usage['cost_usd'],.2)
 def test_timeout_not_retried(self):
  a=self.agent()
  with patch('rate_limits.time.sleep'),patch('rate_limits.urllib.request.urlopen',side_effect=TimeoutError()) as f:
   with self.assertRaises(TimeoutError):request_json(a,None,.1,0)
   self.assertEqual(f.call_count,1)
 def test_budget_prevents_retry(self):
  a=self.agent();a.max_cost=.1
  with patch('rate_limits.time.sleep'),patch('rate_limits.urllib.request.urlopen',side_effect=urllib.error.HTTPError('x',429,'rate',{},None)) as f:
   with self.assertRaises(RuntimeError):request_json(a,None,.1,0)
   self.assertEqual(f.call_count,1)
 def test_bounded_attempts(self):
  a=self.agent()
  with patch('rate_limits.time.sleep'),patch('rate_limits.urllib.request.urlopen',side_effect=urllib.error.HTTPError('x',429,'rate',{},None)) as f:
   with self.assertRaises(urllib.error.HTTPError):request_json(a,None,.1,0)
   self.assertEqual(f.call_count,4)
 def test_error_diagnostics_redact_secret(self):
  a=self.agent();a.key='test-private-key'
  payload=b'{"error":{"message":"failed test-private-key user_123", "metadata":{"provider_name":"Example", "raw":"secret", "limit_source":"provider"}}}'
  err=urllib.error.HTTPError('x',429,'rate',{'Retry-After':'400'},io.BytesIO(payload))
  with patch('rate_limits.time.sleep'),patch('rate_limits.urllib.request.urlopen',side_effect=err):
   with self.assertRaises(urllib.error.HTTPError):request_json(a,None,.1,0)
  diagnostic=a.retry_events[0]['diagnostic']
  self.assertEqual(diagnostic['provider_name'],'Example')
  self.assertNotIn('test-private-key',str(diagnostic));self.assertNotIn('user_123',str(diagnostic));self.assertNotIn('raw',diagnostic)
 def test_non_rate_http_error_not_retried(self):
  a=self.agent()
  with patch('rate_limits.time.sleep'),patch('rate_limits.urllib.request.urlopen',side_effect=urllib.error.HTTPError('x',402,'budget',{},io.BytesIO(b'{}'))) as f:
   with self.assertRaises(urllib.error.HTTPError):request_json(a,None,.1,0)
   self.assertEqual(f.call_count,1)
 def test_retry_after_parsing(self):
  self.assertEqual(retry_delay('60',0),60)
  self.assertEqual(retry_delay(None,2),120)
