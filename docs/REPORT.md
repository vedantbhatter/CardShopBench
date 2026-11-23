# CardShopBench: baseline validation report

This release evaluates deterministic strategies in a snapshot-initialized simulation, not LLMs or real transactions. All 135 episodes completed. The dataset contains 75 observed aggregate card-price references.

| Scenario | Execution | Margin buyer profit | Hype chaser profit | Cash hold |
|---|---|---:|---:|---:|
| mixed | conservative | $35.33 | $2.55 | $0.00 |
| mixed | base | $124.49 | $67.60 | $0.00 |
| mixed | optimistic | $171.78 | $83.36 | $0.00 |
| reprint | conservative | $21.98 | $-64.26 | $0.00 |
| reprint | base | $112.30 | $7.07 | $0.00 |
| reprint | optimistic | $158.51 | $29.88 | $0.00 |
| hype | conservative | $22.46 | $-67.52 | $0.00 |
| hype | base | $120.51 | $8.28 | $0.00 |
| hype | optimistic | $177.39 | $33.77 | $0.00 |

Means over five matched market seeds. Net profit includes modeled inventory liquidation; it is not realized cash. Inference costs are zero because these are deterministic baselines.

The important result is sensitivity: profitability depends on the chosen execution and market assumptions. See METHODOLOGY.md for the uncalibrated demand formula and sample-selection limitations. Actual model evaluation remains pending provider selection.
