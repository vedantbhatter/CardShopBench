# CardShopBench

**Can an AI turn a trading-card collection into a business?**

[Interactive report](https://vedantbhatter.github.io/CardShopBench/) · [Source repository](https://github.com/vedantbhatter/CardShopBench)

CardShopBench is a reproducible environment for evaluating autonomous resale agents. Models research a market, allocate a $1,000 budget, buy inventory, set prices, and manage cash over simulated days. Python owns the accounting and execution; models only choose actions.

**Release status:** working v0.1 research prototype. The bundled report contains **135 executed rule-based baseline episodes**, **75 observed TCGplayer-derived pricing references**, and a **six-model pilot: 12 attempts, six completed episodes, six HTTP-429 interruptions**. All transaction opportunities, price paths after initialization, and sale outcomes are simulated. This is not a validated predictor of real-world returns.

## Measured model pilot — November 23, 2026

[Original run 45282574457](https://github.com/vedantbhatter/CardShopBench/actions/runs/45282574457) · [Original traces](dist/pilot-artifacts.zip) · [Summary and SHA-256 manifest](dist/pilot-summary.json)

Six models, seeds 11 and 22, 14 days, six actions/day, $1,000 simulated starting capital, mixed/base scenario, low reasoning, 4,096 maximum output tokens, pinned providers, and no research corpus. Source commit: `c92f0f37b529cc49ddd01f5b4ab63c52e6374cb8`. The research tool was available but empty; this pilot did not conduct live marketplace trading or forum research.

| Model | Completion | Seed 11 profit | Seed 22 profit | Mean profit | Reported API cost |
| --- | --- | ---: | ---: | ---: | ---: |
| `openai/gpt-6.2-astra` | 0 / 2 · HTTP 429 | — | — | Not ranked | $0.870260 |
| `anthropic/claude-opus-5.5` | 2 / 2 complete | $90.35 | $139.71 | $115.03 | $1.790068 |
| `google/gemini-4-neon` | 2 / 2 complete | $102.72 | $115.76 | $109.24 | $2.458935 |
| `moonshotai/kimi-k3.1-pro` | 0 / 2 · HTTP 429 | — | — | Not ranked | $0.038594 |
| `qwen/qwen3.8-27b` | 2 / 2 complete | $98.73 | $123.76 | $111.25 | $0.252624 |
| `openai/gpt-oss-120b` | 0 / 2 · HTTP 429 | — | — | Not ranked | $0.000098 |

Profit means terminal simulated equity minus initial capital, before inference cost. Incomplete outcomes are not ranked. API costs sum `response.usage.cost` from successful responses across both attempts; they total **$5.4105784899**. Failed-request billing is unavailable. The budget ledger includes conservative reservations and must not be interpreted as actual charges. Prior compatibility spending of approximately $0.065 is separate.

### Matched controls

| Control | Seed 11 profit | Seed 22 profit | Mean profit |
| --- | ---: | ---: | ---: |
| Margin buyer | $14.43 | $19.97 | $17.20 |
| Cash hold | $0.00 | $0.00 | $0.00 |
| Hype chaser | $0.00 | $-16.98 | $-8.49 |

The control files duplicated across six artifacts were checked for equality and deduplicated to six unique episodes. Controls share the pilot's snapshot, seed, initial capital, scenario, regime, horizon, and action budget; they have direct access to public scenario prices rather than the LLM tool interface. The existing 135-episode baseline suite uses 30 days and is retained as a separate sensitivity study.

### Failures and limitations

All six interrupted episodes ended on HTTP 429, not a budget stop. On seed 11, GPT reached day 7 with 42 successful responses, Kimi day 3 with 20, and gpt-oss day 0 with four. Their seed-22 attempts had no successful responses. CI jobs succeeded because result artifacts were saved; this does not imply episode completion.

All three completed models exceeded the margin control on both seeds. Claude recorded 13 invalid actions, Qwen one, and Gemini zero across two episodes. Claude and Qwen sold all purchased units; Gemini's ending equity includes non-cash assets. Two seeds are insufficient for a reliable ranking or significance claim. Synthetic price paths and demand are not calibrated real-market forecasts, and observed differences may depend on provider, token usage, reasoning settings, and this single configuration.

The original run used up to three concurrent jobs and no automatic rate-limit retries. The $1.80 per-episode request guard implied a $21.60 planned maximum; a separate $25 key cap was configured. Subsequent pacing/retry improvements are not part of these results. Original attempts remain available in the trace archive. No additional paid runs were started for this publication.

## Run locally

Python 3.10+; no third-party Python dependencies needed for the core runner.

```bash
python -m unittest discover -s tests -v
python -m cardshopbench.cli suite
python -m http.server 8000 --directory dist
```

Open http://localhost:8000. The checked-in results allow immediate report viewing without running the suite.

```bash
# One baseline episode
python -m cardshopbench.cli run --agent margin --seed 11 --scenario reprint --regime conservative --out runs/margin.json
# Recollect pricing references (network required)
python -m cardshopbench.cli collect --groups 604 2848 23651 --out data/snapshot.json
# Rebuild report data and source download
python -m cardshopbench.cli suite
python scripts/package_source.py
```

## Run an actual model

The adapter uses the OpenRouter Chat Completions API by default; compatible HTTPS endpoints can be configured. Choose a model supporting JSON output. The published pilot includes paid API calls; completion and provider details are recorded below.

Set `CARDSHOPBENCH_API_KEY` using your local shell or secret manager. Never put credentials in source files, the report, or a chat. Optional `CARDSHOPBENCH_API_URL` changes the endpoint. `.env.example` documents names; no automatic dotenv loader is used.

```bash
python -m cardshopbench.cli run \
  --model PROVIDER/MODEL_ID \
  --input-rate CURRENT_INPUT_USD_PER_MILLION \
  --output-rate CURRENT_OUTPUT_USD_PER_MILLION \
  --max-cost 5 --days 30 --seed 11 \
  --out runs/model-seed11.json
```

Replace the uppercase placeholders with your chosen model and current rates. The guard estimates request cost conservatively and enforces a call cap. It is not a substitute for a provider-side hard spend limit: pricing changes, timeout charges, and provider-specific reasoning accounting can differ. No automatic retries are made after ambiguous network failures. Incomplete runs are retained and must not be ranked as completed runs.

To compare models fairly, repeat each model on the same seeds, scenario, regime, prompt, research corpus, and daily action budget. Save exact model IDs and rate configuration. Inference spending is reported separately from simulated business profit.

```bash
python scripts/model_sweep.py --models PROVIDER/MODEL_A PROVIDER/MODEL_B \
  --input-rates 1 1 --output-rates 3 3 --max-cost-per-run 1 --days 5 --seeds 11 22
```

The rates above illustrate syntax, not actual provider prices. The script prints the maximum planned per-run budget total before executing. Use short smoke runs before a full sweep.

## What is implemented

- Public TCGCSV collector, exact product/printing identities, timestamps, snapshot hash and provenance.
- Integer-cent accounting, cash constraints, one-use listings, inventory arrival, sales, fees and settlement delays.
- Three synthetic market scenarios × three execution regimes; event-keyed randomness for paired comparisons.
- Three deterministic controls: cash hold, margin buyer, and hypermodern-focused hype chaser.
- Eight agent actions, persistent notebook, bounded context, request budget checks and environment checkpoints.
- Model-response traces, tool events, profit, drawdown, sell-through and bootstrap intervals.
- Read-only eBay active-listing adapter (requires credentials), reviewed CSV import, dated research corpus retrieval.
- Responsive static report with scenario filters, equity trajectories, decision replay, card search and data/source downloads.
- CI test workflow and an optional manually triggered GitHub Pages workflow.

## Deliberate boundaries

The report separates the **14-day model pilot and matched controls** from the **30-day baseline sensitivity study**. The baselines directly inspect public scenario references; their compute/tool cost is not equivalent to LLM agents. Market snapshot values are aggregate condition-unspecified references, not exact executable quotes. Graded-card/population evaluation requires an additional verified dataset. Raw-condition accuracy, negotiations, returns, counterfeit checks, taxes, multi-agent competition, marketplace reputation, and human-operated baselines are future work.

TCGplayer's direct API is closed to new applicants at time of research. TCGCSV is a third-party public source; this project is not affiliated with either service. eBay Browse provides active listings, not other sellers' historical sold records. Tradepost and Facebook use manual reviewed exports in this release; there is no authenticated live integration. Imported observations are staged separately and do not silently become executable inventory.

See [methodology](docs/METHODOLOGY.md), [data guide](docs/DATA.md), [related work](docs/RELATED_WORK.md), and [roadmap](docs/ROADMAP.md).

## Repository structure

```text
cardshopbench/   accounting environment, agents, data adapters, CLI
scripts/        model sweep and source packaging
 tests/         accounting, reproducibility and adapter checks
 data/          frozen snapshot, evidence examples, import template
 dist/          self-contained report and executed baseline data
 docs/          methodology, provenance, related work and next steps
```

## Publication

Enable GitHub Pages with source **GitHub Actions**, then run the `Publish report` workflow. It deploys the existing `dist/` artifact. Verify results and data permissions before replacing the bundled snapshot. The source archive excludes credentials, local model runs, and hosting identity.

## Attribution

Inspired by [Entrepreneur-Bench](https://mwzhu.github.io/entrepreneur-bench/report.html), [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2), [Project Vend](https://www.anthropic.com/research/project-vend-1), [τ-bench](https://arxiv.org/abs/2406.12045), and [BrowseComp](https://arxiv.org/abs/2504.12516). Pricing references are from [TCGCSV](https://tcgcsv.com/), derived from TCGplayer. Card artwork remains the property of its respective owners. Independent project, not affiliated with Pokémon, Nintendo, or any marketplace.
