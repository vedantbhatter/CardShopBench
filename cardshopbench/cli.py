import argparse
import hashlib
import json
import random
import statistics
from dataclasses import asdict
from pathlib import Path
from .data import collect, collect_sealed, load_snapshot, evidence_before, with_sealed
from .engine import Market, Config
from .agents import Baseline, ModelAgent

def run(snapshot, agent, config, checkpoint=None, evidence=None):
    market = Market(snapshot, config, evidence)
    status, error = 'completed', None
    try:
        while market.day < config.days:
            if market.actions >= config.max_actions:
                market.event('forced_advance', reason='Daily action budget exhausted')
                market.advance()
            else:
                market.act(agent.step(market))
            if checkpoint:
                market.save(checkpoint)
    except Exception as exc:
        status, error = 'incomplete', type(exc).__name__ + ': ' + str(exc)
        if checkpoint:
            market.save(checkpoint)
    return {'agent':agent.name,'agent_type':'baseline' if isinstance(agent,Baseline) else 'llm',
            'status':status,'error':error,'config':asdict(config),'summary':market.summary(),
            'history':market.history,'events':market.events,'usage':agent.usage,
            'model_transcript':getattr(agent,'transcript',[]),
            'snapshot_sha256':snapshot.get('sha256'),
            'evidence_sha256':hashlib.sha256(json.dumps(evidence or [],sort_keys=True).encode()).hexdigest()}

def bootstrap(values):
    rng = random.Random(37)
    means = sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(2000))
    return [round(means[50]), round(means[1949])]

def suite(snapshot):
    runs=[]
    for scenario in ('mixed','reprint','hype'):
        for regime in ('conservative','base','optimistic'):
            for seed in (11,22,33,44,55):
                for agent in ('cash','margin','momentum'):
                    runs.append(run(snapshot,Baseline(agent),Config(seed=seed,regime=regime,scenario=scenario)))
    aggregates=[]
    for scenario in ('mixed','reprint','hype'):
        for regime in ('conservative','base','optimistic'):
            for agent in ('cash','margin','momentum'):
                rows=[r for r in runs if r['agent']==agent and r['config']['scenario']==scenario and r['config']['regime']==regime]
                vals=[r['summary']['profit_cents'] for r in rows]
                aggregates.append({'agent':agent,'scenario':scenario,'regime':regime,'n':len(rows),
                    'mean_profit_cents':round(statistics.mean(vals)), 'bootstrap_ci_cents':bootstrap(vals),
                    'mean_sell_through':statistics.mean(r['summary']['sell_through'] for r in rows),
                    'mean_drawdown':statistics.mean(r['summary']['max_drawdown'] for r in rows)})
    return {'schema_version':1,'status':'baseline validation; no LLM results yet','snapshot':snapshot,
            'runs':runs,'aggregates':aggregates}

MARKETPLACE = dict(days=14, max_actions=10, initial_cents=200000, dms=True)

def marketplace_suite(snapshot):
    """Reference policies on the marketplace track: singles + sealed product + private sellers."""
    runs = [run(snapshot, Baseline(agent), Config(seed=seed, **MARKETPLACE))
            for seed in (11, 22, 33, 44, 55) for agent in ('cash', 'margin', 'trusting', 'verifier')]
    aggregates = []
    for agent in ('cash', 'margin', 'trusting', 'verifier'):
        rows = [r for r in runs if r['agent'] == agent]
        mk = [r['summary']['marketplace'] for r in rows]
        aggregates.append({'agent': agent, 'n': len(rows),
            'mean_profit_cents': round(statistics.mean(r['summary']['profit_cents'] for r in rows)),
            'bootstrap_ci_cents': bootstrap([r['summary']['profit_cents'] for r in rows]),
            'private_deals': sum(m['deals'] for m in mk), 'scams_paid': sum(m['scams_paid'] for m in mk),
            'scam_loss_cents': sum(m['scam_loss_cents'] for m in mk), 'refunds': sum(m['refunds'] for m in mk),
            'injection_payments': sum(m['injection_payments'] for m in mk),
            'scam_offers_seen': sum(m['scam_offers_seen'] for m in mk), 'offers_seen': sum(m['offers_seen'] for m in mk),
            'sealed_units_bought': sum(e['kind'] == 'purchase' and snapshot_kind(snapshot, e['card_id']) != 'single'
                                       for r in rows for e in r['events'])})
    return {'schema_version': 1, 'track': 'marketplace', 'config': MARKETPLACE, 'seeds': [11, 22, 33, 44, 55],
            'aggregates': aggregates, 'runs': [{k: r[k] for k in ('agent', 'config', 'summary')} for r in runs]}

def snapshot_kind(snapshot, card_id):
    return next((c.get('product_type', 'single') for c in snapshot['cards'] if c['id'] == card_id), 'single')

def main():
    parser=argparse.ArgumentParser(description='CardShopBench evaluation runner')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('collect'); p.add_argument('--groups',nargs='+',type=int,default=[604,2848,23651]); p.add_argument('--out',default='data/snapshot.json')
    p=sub.add_parser('collect-sealed'); p.add_argument('--groups',nargs='+',type=int,default=[604,2848,23651]); p.add_argument('--out',default='data/sealed.json')
    p=sub.add_parser('marketplace'); p.add_argument('--snapshot',default='data/snapshot.json'); p.add_argument('--sealed',default='data/sealed.json'); p.add_argument('--out',default='dist/marketplace.json')
    p=sub.add_parser('suite'); p.add_argument('--snapshot',default='data/snapshot.json'); p.add_argument('--out',default='dist/results.json')
    p=sub.add_parser('run'); p.add_argument('--snapshot',default='data/snapshot.json'); p.add_argument('--agent',default='margin'); p.add_argument('--model'); p.add_argument('--days',type=int,default=30); p.add_argument('--seed',type=int,default=11); p.add_argument('--regime',choices=['conservative','base','optimistic'],default='base'); p.add_argument('--scenario',choices=['mixed','reprint','hype'],default='mixed'); p.add_argument('--out',default='runs/run.json'); p.add_argument('--evidence'); p.add_argument('--as-of'); p.add_argument('--no-research',action='store_true'); p.add_argument('--input-rate',type=float,default=0); p.add_argument('--output-rate',type=float,default=0); p.add_argument('--max-cost',type=float,default=5)
    args=parser.parse_args()
    if args.command=='collect':
        result=collect(args.groups,args.out); print(f"Collected {len(result['cards'])} observed references into {args.out}"); return
    if args.command=='collect-sealed':
        result=collect_sealed(args.groups,args.out); print(f"Collected {len(result['cards'])} sealed products into {args.out}"); return
    snap=load_snapshot(args.snapshot)
    if args.command=='marketplace':
        result=marketplace_suite(with_sealed(snap,load_snapshot(args.sealed)))
    elif args.command=='suite':
        result=suite(snap)
    else:
        agent=ModelAgent(args.model,input_rate=args.input_rate,output_rate=args.output_rate,max_cost=args.max_cost) if args.model else Baseline(args.agent)
        evidence=evidence_before(json.loads(Path(args.evidence).read_text()),args.as_of or snap['observed_at']) if args.evidence else []
        result=run(snap,agent,Config(days=args.days,seed=args.seed,regime=args.regime,scenario=args.scenario,research=not args.no_research),args.out+'.checkpoint',evidence)
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(result,indent=2))
    print(f'Saved {args.out}')
    if result.get('status')=='incomplete':
        raise SystemExit(result['error'])

if __name__=='__main__': main()
