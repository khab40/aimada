# Representative scenario benchmark

This table uses AIMADA’s checked-in scenario contracts and the fresh `EXP-18E88EAF` production rerun. The Endpoint rows use the checked-in spoofing and layering requests through the live backend proxy; the Job rows use one completed Nebius Serverless Job. No ad-hoc scenario path or extra production workload was used.

| Scenario | Expected | Observed | Request / response evidence | Endpoint request or Job run | Status |
|---|---|---|---|---|---|
| benign MM | benign | `benign_market_making` (confidence 0.90); Job had 0 alerts for `normal_market` | [standard request/response fixture](../../serverless/endpoint/examples/benign-market-making.json) | [EXP-18E88EAF metrics](../../outputs/benchmark/EXP-18E88EAF/detector_metrics.csv); Job `aijob-e00q7cdpz32jyk0bsg` in [jobs.json](../../outputs/benchmark/EXP-18E88EAF/jobs.json) | ✅ |
| spoofing | spoofing | Live Endpoint: `spoofing_like`, confidence 0.85, structured assessment, no fallback; Job: precision 1.0, recall 1.0, F1 1.0, 1/1 alert | [standard request/response fixture](../../serverless/endpoint/examples/spoofing.json); live [request](../../outputs/benchmark/EXP-18E88EAF/endpoint-spoofing-request.json) and [response](../../outputs/benchmark/EXP-18E88EAF/endpoint-spoofing-response.json) | Endpoint EVD `EVD-EA016D5A3647`; [EXP-18E88EAF benchmark report](../../outputs/benchmark/EXP-18E88EAF/benchmark_report.md) | ✅ |
| layering | layering | Live Endpoint: `layering_like`, confidence 0.89, structured assessment, no fallback; Job: precision 1.0, recall 1.0, F1 1.0, 1/1 alert | [standard request/response fixture](../../serverless/endpoint/examples/layering.json); live [request](../../outputs/benchmark/EXP-18E88EAF/endpoint-layering-request.json) and [response](../../outputs/benchmark/EXP-18E88EAF/endpoint-layering-response.json) | Endpoint EVD `EVD-DDB7E7683A8F`; [EXP-18E88EAF benchmark report](../../outputs/benchmark/EXP-18E88EAF/benchmark_report.md) | ✅ |
| detector disagreement | uncertainty | `inconclusive_one_sided_liquidity_withdrawal`, confidence 0.56 | [standard uncertainty request/response fixture](../../serverless/endpoint/examples/uncertain.json) | No new endpoint request; contract fixture has conflicting spoofing/layering scores and no ground truth | ✅ |
| low liquidity | suspicious | standard `pump_and_cancel` Job produced no alert: TP 0, FN 1, recall 0.0 | [standard scenario alias](../../serverless/jobs/detector_tournament.py) | [EXP-18E88EAF metrics](../../outputs/benchmark/EXP-18E88EAF/detector_metrics.csv) and [benchmark report](../../outputs/benchmark/EXP-18E88EAF/benchmark_report.md) | ⚠️ |

## What was done

The standard spoofing and layering fixtures were converted into the backend’s structured investigation request and sent through the live Endpoint. The five standard scenarios were submitted once to Job `aijob-e00q7cdpz32jyk0bsg` using image `ghcr.io/khab40/ai-market-abuse-detection-arena-jobs:artifacts-v3-20260714-151355`, `cpu-d3`, and `4vcpu-16gb`. The Job ran from `2026-07-14T17:33:35Z` to `2026-07-14T17:36:36Z` (~181 seconds); seven S3 artifacts were synchronized with no missing files. Evidence records the request source, observed response or detector result, execution source, and status.

## Explanation by the system

- **benign MM:** the system explains balanced two-sided quoting and regular executions as benign liquidity provision; the production benchmark retained this as a no-alert control.
- **spoofing:** the system explains near-touch displayed pressure, replenishment, low execution, cancellation, and price reversion as spoofing-like evidence.
- **layering:** the system explains coordinated multi-level same-side depth and progressive cancellation as layering-like evidence.
- **detector disagreement:** the system explicitly reports uncertainty because detector scores conflict and ground truth is absent; it does not claim manipulation.
- **low liquidity:** the standard `pump_and_cancel` production Job missed its one labeled run. This is a recorded benchmark gap, not a fabricated success.

The current production rerun covers five requested workloads, four normalized attacks, one completed Nebius Job, two successful live Endpoint investigation calls, and seven synchronized Job artifacts. Fixture responses remain integration contracts and must not be read as real-market accuracy claims.

The completed production Job is `aijob-e00q7cdpz32jyk0bsg` (see [jobs.json](../../outputs/benchmark/EXP-18E88EAF/jobs.json)). Each record above has an explicit request source, response source, action performed, execution source, and system explanation; no private credentials or signed URLs are included.
