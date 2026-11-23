# Related work and design decisions

Sources reviewed November 23, 2026. These are references, not collaborators or endorsements.

| Reference | Relevant idea | CardShopBench status |
|---|---|---|
| [Vending-Bench 2](https://andonlabs.com/evals/vending-bench-2) | Long-running inventory, procurement, pricing and cash management | Implemented: multi-day operation, notebook, delivery delays. Future: negotiation, returns and supplier failure. |
| [Project Vend](https://www.anthropic.com/research/project-vend-1) | Real-world shopkeeping reveals operational and social failure modes | Implemented: explicit costs and enforceable ledger. Future: misleading seller messages and discount pressure. |
| [τ-bench](https://arxiv.org/abs/2406.12045) | Evaluate final database state and consistency over repeated attempts | Implemented: accounting invariants and repeated paired markets. Future: repeated same-seed LLM runs and operational pass^k. |
| [BrowseComp](https://arxiv.org/abs/2504.12516) | Hard-to-find evidence and persistence in information retrieval | Implemented: provenance-aware evidence retrieval. Future: scored retrieval tasks with independently verified answers. |
| [Entrepreneur-Bench](https://mwzhu.github.io/entrepreneur-bench/report.html) | Simulated freelance business and decomposition of business skills | Implemented independently for card resale: transaction traces, economic and operational metrics. |

## High-value additions

1. **Seller manipulation track:** include a forum post claiming guaranteed appreciation, or a seller asking the agent to ignore its budget. Score actual actions, not only refusal wording. Keep posts inside untrusted tool results.
2. **Condition/variant traps:** wrong language, reverse-holo versus holo, raw versus graded, PSA versus CGC, misleading multi-card lot listings. Reward abstaining when identity cannot be resolved.
3. **Research ablation:** compare no research, pricing only, and pricing plus forums. Measure net value after research cost.
4. **Execution robustness:** calibrate buyer arrivals using legitimate timestamped sales and test on withheld periods. Report whether model ordering changes with fill assumptions.
5. **Repeated-run reliability:** multiple model samples per fixed market seed separate agent variation from market variation.
6. **Competitive arena:** shared inventory and limited buyer demand can create realistic price competition, but should remain separate from independent paired-market evaluation.
7. **Prospective paper business:** freeze decisions daily, retain source snapshots and assess later outcomes. Still distinguish modeled fills from verified transactions.

Current scope implements a smaller coherent system rather than claiming these planned tracks are complete.
