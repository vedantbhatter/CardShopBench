# Methodology v0.1

## Question
Can an agent consistently operate a profitable resale business under explicitly modeled market constraints? The current release validates the environment with deterministic strategies before conducting LLM comparisons.

## Separation of observation and simulation
75 references were collected from TCGCSV in November 2026: 25 eligible product/printing variants each from Base Set, Evolving Skies, and Surging Sparks. Products must have a card number and an aggregate market reference between $5 and $500. Selection sorts descending by reference price. This is an intentionally limited, biased universe, not a representative sample. Raw condition and liquidity are unknown. No PSA population facts are inferred.

The snapshot initializes reference prices. Every later price path, available purchase, and buyer arrival is synthetic. Thus this is a **snapshot-initialized simulation**, not historical replay or paper trading. Scenario returns cannot establish market predictability.

## Time and actions
An episode lasts 30 simulated days, with $1,000 in settled cash. Each day allows 12 actions. `end_day` advances time; exhausting actions forces an advance and logs it. Listings have one unit and expire when the day changes. New synthetic asks range from 65% to 111% of the scenario reference. All assets use the same illustrative execution model in v0.1; actual segment liquidity is unknown.

Purchases immediately debit asking price plus $1 inbound cost. Inventory arrives after two days. Only arrived inventory may be listed. One price update applies to an owned item; no short selling or borrowing. A sale creates a receivable that settles two days later. Fees are rounded in cents: 13.25% of gross plus $4.50 outbound shipping. Fee assumptions are configurable and are not a marketplace-specific fee schedule.

## Exogenous randomness
SHA-256 of `(seed,event_type,day,listing_slot_or_id)` produces a reproducible uniform draw. Research calls cannot consume random draws or change which listings arrive. Each agent receives an independent copy of the same market realization. This is not a competitive shared order book.

## Scenario paths
- Mixed: a deterministic daily reference increase of 0.2% for hypermodern and 0.04% otherwise.
- Reprint: the mixed path with a 28% hypermodern reference reduction beginning on day 12.
- Hype: hypermodern prices rise to day 12, hold briefly, then fall to 84% of the mixed reference from day 16.

These are designer-authored stress scenarios, not fitted market trends. The exact scenario rules are public, making this an open-book planning test, not a surprise forecasting test. Future hidden holdout paths should evaluate generalization.

## Execution
For asking/reference ratio r, daily sale probability is `min(0.85, 0.25 * demand_multiplier * exp(-7*(r-1)))`, with bounded exponent to avoid numeric overflow. Demand multipliers are 0.55 / 1 / 1.4 for conservative / base / optimistic. Individual listings are independent; aggregate buyer-volume capacity is not modeled. This is uncalibrated and can be exploited by strategies optimized for its rules. Report sensitivity rather than claiming realistic sell-through.

Inventory liquidation applies a 65% / 75% / 85% reference multiplier, then estimated selling fees and shipping. Pending inventory is included with the same haircut; delivery/default risk is not modeled. Receivables are treated as collectible. Terminal value is not realized cash.

## Metrics
- Final equity = settled cash + outstanding receivables + estimated inventory liquidation.
- Net profit = final equity minus starting capital.
- Realized profit = net completed sale proceeds minus the cost basis of sold items.
- Sell-through = units sold / units purchased; zero if none purchased.
- Maximum drawdown = largest percentage decline from the prior running equity peak.
- Invalid actions and model token costs are separate operational metrics.

The report shows 5 paired seeds for each of 3 baselines, 3 scenarios and 3 regimes: 135 episodes. Bootstrap intervals resample five episode profit values 2,000 times with a fixed seed; 2.5th and 97.5th percentile endpoints are approximate. These small-sample intervals are exploratory and exclude data-quality, simulator-model, and real-world uncertainty. Shared seeds support paired comparison, but the displayed intervals are marginal, not confidence intervals for pairwise differences. No statistically significant model-superiority claims are made.

## Agent harness
A model receives current portfolio/rules, its persistent notebook and the latest eight events. It emits one structured JSON action with a brief justification. The adapter uses an HTTPS Chat Completions endpoint, an 800-output-token cap, request-count and estimated-dollar guards, and a 60-second timeout. Input history is bounded; this release does not implement provider prompt-cache optimization. Raw responses, usage and latencies are recorded. No hidden chain-of-thought is requested.

The framework saves environment checkpoints after actions. `Market.restore` reconstructs deterministic environment state; full model-provider conversation/budget resumption is not yet exposed as a CLI operation. Failed requests produce incomplete runs instead of inventing decisions. Live provider calls remain unverified until credentials are supplied.

## Research protocol
Evidence records include source URL, content, observation time, publication cutoff and evidence type. The loader gates both publication and observation against the chosen evaluation cutoff. If exact publication time is unavailable, acquisition time is used conservatively; it is not presented as the actual publication timestamp. Forum opinions do not change the simulator's true market process and cannot be treated as observed sales.

Research ablation: run the same model, seeds, prompt and cost budget with `--no-research` and with a frozen corpus. Report performance differences and sources actually retrieved. This experiment has not yet been run. A future historical protocol must withhold future documents and consider model-training leakage and survivorship bias.
