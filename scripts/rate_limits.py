"""Bounded 429 retry transport. Never retries ambiguous timeouts or other errors."""
import json,time,urllib.request,urllib.error,re,math
from email.utils import parsedate_to_datetime
from datetime import datetime,timezone

def retry_delay(value,attempt):
 try: delay=float(value)
 except (TypeError,ValueError):
  try: delay=(parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds()
  except (TypeError,ValueError,OverflowError):delay=30*2**attempt
 return max(1,delay) if math.isfinite(delay) else 300

def request_json(agent,request,reserve,day):
 for attempt in range(4):
  if agent.usage['cost_usd']+reserve>agent.max_cost:raise RuntimeError('Episode budget reached including retry reservations')
  time.sleep(5)
  agent.calls+=1;agent.usage['cost_usd']+=reserve
  try:
   with urllib.request.urlopen(request,timeout=90) as response:return json.load(response)
  except urllib.error.HTTPError as exc:
   try:
    error=json.loads(exc.read(16384)).get('error',{})
   except (ValueError,TypeError):error={}
   if not isinstance(error,dict):error={}
   metadata=error.get('metadata',{})
   if not isinstance(metadata,dict):metadata={}
   diagnostic={k:metadata[k] for k in ('provider_name','provider_code','error_type','limit_source') if isinstance(metadata.get(k),(str,int,float))}
   # Store only diagnostic fields, never raw provider payloads or account IDs.
   message=str(error.get('message',''))
   if getattr(agent,'key',None):message=message.replace(agent.key,'[REDACTED]')
   message=re.sub(r'(?:sk-[A-Za-z0-9_-]+|Bearer\s+\S+|user_[A-Za-z0-9_-]+)','[REDACTED]',message)
   diagnostic['message']=message[:500]
   delay=retry_delay(exc.headers.get('Retry-After'),attempt)
   agent.retry_events.append({'day':day,'attempt':attempt+1,'status':429,'wait_seconds':delay,'reserved_usd':reserve,'diagnostic':diagnostic})
   # Keep failed-attempt reservations: do not assume rejected requests were free.
   if exc.code!=429 or attempt==3 or delay>300:raise
   time.sleep(delay)
