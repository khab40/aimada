# Representative scenario benchmark

This table uses AIMADA’s checked-in scenario contracts and the committed `EXP-390EFAC2` production benchmark. No ad-hoc scenario path or additional Nebius inference was used after the interrupted exploratory request. The fixture rows validate the request/response contract; the Job rows are execution evidence.

| Scenario | Expected | Result | Request / response evidence | Endpoint request or Job run | Status |
|---|---|---|---|---|---|
| benign MM | benign | `benign_market_making` (confidence 0.90); production Job had 0 alerts for `normal_market` | [standard request/response fixture](../../serverless/endpoint/examples/benign-market-making.json) | [EXP-390EFAC2 metrics](../../outputs/benchmark/EXP-390EFAC2/detector_metrics.csv); completed Jobs are listed in [jobs.json](../../outputs/benchmark/EXP-390EFAC2/jobs.json) | ✅ |
| spoofing | spoofing | `spoofing_like`; production metrics: precision 1.0, recall 1.0, F1 1.0, 20/20 alerts | [standard request/response fixture](../../serverless/endpoint/examples/spoofing.json) | [EXP-390EFAC2 benchmark report](../../outputs/benchmark/EXP-390EFAC2/benchmark_report.md) | ✅ |
| layering | layering | `layering_like`; production metrics: precision 1.0, recall 1.0, F1 1.0, 20/20 alerts | [standard request/response fixture](../../serverless/endpoint/examples/layering.json) | [EXP-390EFAC2 benchmark report](../../outputs/benchmark/EXP-390EFAC2/benchmark_report.md) | ✅ |
| detector disagreement | uncertainty | `inconclusive_one_sided_liquidity_withdrawal`, confidence 0.56 | [standard uncertainty request/response fixture](../../serverless/endpoint/examples/uncertain.json) | No new endpoint request; contract fixture has conflicting spoofing/layering scores and no ground truth | ✅ |
| low liquidity | suspicious | canonical `liquidity-evaporation` local Job produced no alert: TP 0, FN 1, recall 0.0 | [standard scenario alias](../../serverless/jobs/detector_tournament.py); stdout metrics recorded during this run | `detector_tournament.py --runs 1 --scenarios liquidity_evaporation --random-seed 42` (local CPU, no Nebius spend) | ⚠️ |

## What was done and system explanation

- **benign MM:** the system explains balanced two-sided quoting and regular executions as benign liquidity provision; the production benchmark retained this as a no-alert control.
- **spoofing:** the system explains near-touch displayed pressure, replenishment, low execution, cancellation, and price reversion as spoofing-like evidence.
- **layering:** the system explains coordinated multi-level same-side depth and progressive cancellation as layering-like evidence.
- **detector disagreement:** the system explicitly reports uncertainty because detector scores conflict and ground truth is absent; it does not claim manipulation.
- **low liquidity:** the standard local detector run missed the canonical liquidity-evaporation label. This is a recorded benchmark gap, not a fabricated success.

The production Job evidence covers 100 requested workloads, 80 normalized attacks, two completed Nebius Jobs, and seven successful Nebius Endpoint investigation summaries. Fixture responses are integration contracts and must not be read as real-market accuracy claims.

The completed production Job IDs are `aijob-e00cygzs8f63h4dg2z` and `aijob-e00qq10wjz0p5karsp` (see [jobs.json](../../outputs/benchmark/EXP-390EFAC2/jobs.json)). Each record above therefore has an explicit request source, response source, action performed, execution source, and system explanation; no private credentials or signed URLs are included.
