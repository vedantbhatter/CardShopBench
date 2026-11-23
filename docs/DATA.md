# Data and integrations

## Observed snapshot
`data/snapshot.json` includes source URLs, retrieval timestamps, product IDs, print variants, selected groups, a SHA-256 digest of normalized cards, and explicit limitations. Source: https://tcgcsv.com/. TCGCSV provides daily TCGplayer-derived product/pricing files and explicitly excludes condition-level SKUs. The collector stores market reference values without claiming individual sales. `dist/snapshot.json` mirrors the report's data.

Definitions for this project's era tags: vintage through 2003, modern 2004–2022, hypermodern 2023 onward, based on group publication year. These are project definitions, not universal collector terminology. Population and liquidity fields remain null because no evidence supports them.

## eBay active listings
```bash
# Set EBAY_ACCESS_TOKEN locally using approved eBay application credentials.
python -m cardshopbench.connectors ebay 'pokemon pikachu' --out data/ebay-observations.json
```
This read-only adapter uses Browse item search. Output is marked `asking_price`, with `card_id: null` and `review_status: unmatched`. Shipping is not included. It does not perform OAuth itself, query sold data, or make purchases. Exact identity and condition matching require review. Credentialed behavior has not been exercised in this release.

Official documentation: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search

## Tradepost, Facebook and reviewed observations
Copy `data/import-template.csv`, add reviewed rows, then:
```bash
python -m cardshopbench.connectors import your-export.csv --out data/reviewed-observations.json
```
Required: source, HTTPS provenance URL, timezone-aware observed_at, reviewed card_id, name, variant, condition, positive integer price_cents, and explicit observation_kind (asking_price / sold_price / aggregate_market_reference). These files are staged observations, not automatically added to the simulator's purchase stream. No Facebook scraping or automatic Tradepost connection is shipped.

Tradepost's published trading-card schema is under active development: https://tpx.tradepost.co/trading-card/
TCGplayer access status: https://docs.tcgplayer.com/docs/getting-started

## Forum evidence
`data/research.json` contains a small manually reviewed starter corpus of public discussion summaries, not an exhaustive trend survey. It is untrusted sentiment; no quoted number is independently verified. Both publication cutoff and observed_at must precede evaluation `--as-of`. Run with a cutoff after corpus acquisition:
```bash
python -m cardshopbench.cli run --agent margin --evidence data/research.json --as-of 2026-11-24T00:00:00+00:00
```
Baselines ignore research; use a real model to evaluate whether research changes decisions. The specified date is an example cutoff, not evidence of data available earlier. Research retrieval is lexical and capped at eight results. Future work: sanctioned forum feeds, deduplication, source quality ranking, targeted collection, and claim-to-comparable matching.

## Data distribution
Project code and third-party data are separate. The source download includes the small attributed derived snapshot for reproducibility; original artwork is linked from the source and not relicensed. Review provider terms before collecting at scale or redistributing additional data. Never include private Facebook messages, personal seller details, or access tokens in published artifacts.
