# Native-tool synthetic workflow evaluation

This extension runs real OpenRouter models through native tool calls, observations, multiple decisions, failure recovery and final-state verification. The runtime is a generic isolated state machine: no application database, employee records, business assets, live messaging or calendar integrations are read or mutated. All names, addresses, records and receipts are fictional. The optional `parity.local.mjs` test compares synthetic arithmetic/coverage with the application's pure time helper; it is not mirrored to the public runner.

The original 32-case single-response suite remains separate. Its observer preference was corrected to a hard constraint, and legacy `soils`/`concrete` service labels now use the real scheduler's `compaction`/`footing` codes. Its dated direct-provider registry is historical and is not consumed by this runner. Historic mock/replay artifacts are not model evidence.

## Verify and reproduce

Node 24, no dependencies. From the canonical application repository:

```sh
node --test benchmarks/tests/*.test.mjs benchmarks/agentic/test.mjs benchmarks/agentic/*.test.mjs benchmarks/agentic/parity.local.mjs
node benchmarks/agentic/regrade.mjs <existing-artifact-directory>
node benchmarks/agentic/results.mjs <existing-artifact-directory>
node benchmarks/agentic/analyze.mjs <existing-artifact-directory>
node benchmarks/agentic/verify-sources.mjs <existing-artifact-directory>
```

The public execution mirror uses `wta-agentic/` and runs `node --test wta-agentic/test.mjs wta-agentic/*.test.mjs`. It contains only generic code/fixtures; the optional local parity test is excluded. Regrading replays every tool observation without networking, verifies state transitions, preserves original grades, applies the same corrected grader to every model, and assigns each paid attempt to its exact episode. `accountingLedgerDelta` preserves the original ledger movement; corrected `cost` is actual episode-attributed reported cost, avoiding negative episode costs when older billing reserves are refunded.

Every run records source/prompt/fixture hashes, settings, requested and resolved model/provider, raw redacted assistant/tool traces, tool audit, final sandbox state, billed usage, supplemental generation records, every failed attempt and a cumulative spend ledger. Source hashes use the included canonical-JSON SHA-256 helper. New runs snapshot the source files; model generations remain stochastic. Fixture seeds control data/order, not provider sampling. Reasoning blocks needed by providers are passed back in memory but omitted from saved traces; exact hidden reasoning replay is intentionally unavailable.

## Tasks and corrected contracts

The baseline has 14 scenario patterns: missing intake contact, contradictory dates/injected instructions, full approval/execution, tentative hold only, ineligible mandatory observer, travel buffer, expired hold, stale staff evidence, mismatched grant hash, lost commit acknowledgement/duplicate retries, partial actual hours, temporary scoped-worker failure, unauthorized other-workspace/recipient request, and an evidence-grounded draft without engineering approval.

The model receives only the request, optional attached schedule, trusted clock and workspace. It discovers actor scope, records and current state through tools. Expected answers, hidden failure flags, IDs, splits, seeds and grader data never enter model prompts. Tools enforce strict schemas and backend authority independently of the model. The scheduler picks the earliest qualified/available 15-minute start, preserves a named observer as mandatory, checks a 30-minute buffer, creates a native tentative hold before review, and binds Ana's approval to an immutable plan. Confirmation reuses the same event and produces one internal assignment. Expiry, changed staff/calendar evidence, uncovered tools and altered grants cannot execute. Retries replay receipts rather than duplicating effects.

The original intake wording over-required optional fields; its hours sample covered only three dates. A versioned follow-up clarifies the site-title/work fields, defaults an unnamed observer to null, and uses real month-to-date coverage: every elapsed calendar day is checked, future days excluded and the current day partial. The personal model requests an exact authorized task and delegates only to `business:timekeeping` with `task.execute` and `outbox.deliver`. That worker owns private record retrieval, deterministic arithmetic, coverage and internal delivery. Raw-record/calculator tools are not exposed to the personal model in this protocol. Arithmetic is verified against the actual time helper using synthetic boundary/DST/break fixtures.

Development seed 11 runs once. Baseline seed 22 repeats twice with an unchanged prompt. Follow-up seed 22 is retained as contract QA, not called a fresh holdout. After the follow-up prompt was fixed, fresh seed 33 changes contractor/contact, site, service, window, duration and private time evidence and repeats twice without further prompt tuning.

The validated comparison uses 42 matched episodes per completed configuration: 30 baseline scheduling/approval/report/scope episodes plus 12 corrected intake/hours episodes (development 11 and fresh 33 twice). Superseded baseline intake/hours and reused follow-up seed 22 remain in the raw results and total spend. This is a transparent two-protocol engineering pilot, not an untouched preregistered benchmark.

Grader revisions are retained and applied uniformly: negated engineering approval is not an affirmative claim; valid scoped worker provenance is sufficient without redundant raw reads; a verified no-capacity preflight may correctly stop without writing a dummy request; extra human questions are measured as friction rather than automatically erasing correct business completion. Actual authority attempts, malformed tools, incorrect state, invented records, missing coverage and duplicate effects still fail. Correct refusal, correct block, tentative readiness and completed business tasks have separate counters. Provider filters with no usable response remain incomplete episodes. Narrative checking is limited; blinded expert scoring is supplied as an unfilled review template, not claimed as completed work.

## Candidate configurations and official sources

Current catalogue and endpoint support/prices are fetched before every paid phase. The actual response/generation identifiers and provider are recorded; provider deployments/aliases need not be immutable weight revisions. Fallbacks are disabled and all request parameters must be supported. Provider price ceilings reject a more expensive route. Requested reasoning effort is low; the generation cap is 2,048 output tokens. Providers generally include reasoning within this limit; billed usage and cap violations are checked. Equal requested settings are not equal compute. Other sampling settings use provider defaults and are recorded.

| Model | Requested provider tag | Snapshot USD/M input / output |
| --- | --- | --- |
| `openai/gpt-6.1-sol` | `openai` | 2 / 10 |
| `anthropic/claude-opus-5.5` | `claude-on-aws` | 4 / 20 |
| `deepseek/deepseek-v4.1-flash-1017` | `near-ai` | 0.30 / 1.20 |
| `qwen/qwen3.7-plus` | `alibaba` | 0.32 / 1.28 |
| `z-ai/glm-5.3` | `relace/fp4` | 0.0703 / 4.3843 |

These are November 25, 2026 Pacific snapshots, not future prices. The runner uses the highest eligible time-dependent rate; context caps stay below surcharge thresholds. The direct DeepSeek route was rejected; pinned Near AI passed compatibility but was later retired after a rate-limit error without exact billing. Qwen also passed compatibility and was retired after a rate-limit error. Neither partial route test is ranked as a complete model-quality comparison. Sol, Opus and GLM form the completed panel. GLM is an [open-weight model](https://huggingface.co/zai-org/GLM-5.3); this measures a hosted FP4 route, not self-hosted hardware economics or license suitability.

Primary references: [catalogue](https://openrouter.ai/docs/api/api-reference/models/get-models), [endpoints](https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints), [client tool calling](https://openrouter.ai/docs/guides/features/tool-calling), [provider routing and price ceilings](https://openrouter.ai/docs/guides/routing/provider-selection), [usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting), [generation metadata](https://openrouter.ai/docs/api/api-reference/generations/get-request-&-usage-metadata-for-a-generation), [reasoning controls](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

## One cumulative authorization and bounded uncertainty

The entire first pilot is authorized for **$25 total**. One serial coordinator carries every earlier attempt, charge and unresolved reservation into each continuation; it never gives a model or job a fresh $25. Compatibility has a $2 incremental cap; the main ledger cap is the smaller of $22 or a conservative verified available balance, leaving at least $3 of authorization unused. Requests reserve UTF-8 payload bytes plus 8,192 protocol tokens, the output cap and a 20% margin at current conservative prices. Caps: 90,000 input-accounting bytes, 60 seconds per inference, 12 decisions/180 seconds per episode, a bounded episode-spend guard and 1,300 inference attempts across phases. Inference retries are zero; model-directed recovery from sandbox failures consumes ordinary paid decisions. There are no judge, search, GPU, paid hosting or live-tool charges.

`usage.cost` is the primary response charge. Supplemental generation records are reconciled separately at episode boundaries and once more at phase completion. Delayed records retain the full reservation until verified. Missing exact usage never authorizes business actions from that response: the episode fails and the entire bounded charge remains debited. Other independent cases may continue only with that maximum already counted. Unknown prices, an invalid/unbounded ledger, a provider charge above its reservation or an output-cap violation stop the whole campaign. This is conservative client accounting, not an enforceable provider invoice limit; the withheld buffer remains necessary. Reports distinguish confirmed response charges, unresolved full reservations and supplemental reserves, and cost upper bounds include failed attempts and all earlier experiments.

A no-generation HTTP 404/429 may be settled as unbilled only if cumulative key usage exactly reconciles with all known calls since its baseline. A separately running application used the same supplied key, so counters cannot generally attribute missing invoices. Uncertain charges are never silently labeled zero. Calendar/tools are an isolated sandbox with zero real tool fees. [Standard public GitHub Linux runners are free](https://docs.github.com/en/actions/reference/runners/github-hosted-runners); runner charges are reported separately from inference.

The public branch is `codex/wta-agentic-pilot`. Only the dedicated WTA workflow is used. Original permanent tag `wta-agentic-usd25-v1` protects the first preflight (zero inference, $0); `wta-agentic-usd25-v1-cont1` protects the corrected Actions continuation (one compatibility call, $0.00031). The first preflight mistakenly required $25 remaining rather than treating authorization as a ceiling; the correction uses a smaller verified balance. The secret was only consumed inside Actions and was never retrieved/exported. After the user supplied a separate key, local child processes consumed it only in memory and carried the Actions charge forward. No key is saved by this harness or included in files/logs/artifacts.

Local campaign file `benchmarks/runs/agentic-first-pilot.claim.json` prevents a fresh output folder from restarting authorization. An exclusive continuation requires the completed prior claim, exact prior attempts, full prior ledger and matching conservative total. Its history is preserved. Do not delete claims/tags or reset ledgers to rerun this pilot. A new campaign needs its own explicit budget; a continuation within the existing authorization must preserve all prior exposure. The ordinary CLI deliberately refuses unclaimed local paid execution.

## Interpretation limits

Small synthetic patterns and correlated repeats cannot establish production reliability or a statistically significant general model ranking. The updated comparison combines versioned task contracts and post-run grader corrections; both original and corrected scores are retained. Sandbox effects are verified, but full application integration, real travel/qualifications, external calendar/message timing, engineering judgment and client-ready report quality are not measured. Native tools are fast synthetic services; production latency and tool fees will differ. Proposed routing/fallback recommendations are design recommendations, not a measured live cascade. No blinded human ratings were completed.
