"""Read-only acquisition adapters. No purchase, listing, or messaging APIs."""
import argparse
import csv
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

REQUIRED = ('source','source_url','observed_at','card_id','name','variant','condition','price_cents','observation_kind')

def import_csv(path):
    with open(path,newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        if not set(REQUIRED).issubset(reader.fieldnames or []):
            raise ValueError('Missing columns: '+', '.join(REQUIRED))
        result=[]
        for row in reader:
            if row['observation_kind'] not in ('asking_price','sold_price','aggregate_market_reference'):
                raise ValueError('Explicit observation_kind required')
            if not row['source_url'].startswith('https://'):
                raise ValueError('HTTPS provenance URL required')
            when=datetime.fromisoformat(row['observed_at'].replace('Z','+00:00'))
            if when.tzinfo is None:
                raise ValueError('Timezone required')
            row['price_cents']=int(row['price_cents'])
            if row['price_cents']<=0 or not row['card_id']:
                raise ValueError('Positive price and reviewed card identity required')
            row['review_status']='user_imported'
            result.append(row)
    return result

def ebay_search(query, limit=25):
    token=os.environ.get('EBAY_ACCESS_TOKEN')
    if not token: raise ValueError('EBAY_ACCESS_TOKEN is required; use your approved application credentials')
    url='https://api.ebay.com/buy/browse/v1/item_summary/search?'+urllib.parse.urlencode({'q':query,'limit':min(50,max(1,limit))})
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'X-EBAY-C-MARKETPLACE-ID':'EBAY_US'})
    with urllib.request.urlopen(req,timeout=30) as response: data=json.load(response)
    now=datetime.now(timezone.utc).isoformat()
    return [{'source':'eBay Browse','source_url':x['itemWebUrl'],'observed_at':now,
        'external_id':x['itemId'],'name':x['title'],'currency':x['price']['currency'],
        'price_cents':int(Decimal(x['price']['value'])*100),'condition':x.get('condition','unknown'),
        'observation_kind':'asking_price','review_status':'unmatched',
        'card_id':None,'shipping_included':False} for x in data.get('itemSummaries',[])]

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('import'); x.add_argument('csv'); x.add_argument('--out',required=True)
    x=sub.add_parser('ebay'); x.add_argument('query'); x.add_argument('--out',required=True)
    a=p.parse_args(); rows=import_csv(a.csv) if a.command=='import' else ebay_search(a.query)
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(rows,indent=2))
    print(f'Saved {len(rows)} observations. Review identity before using in a benchmark.')
if __name__=='__main__': main()
