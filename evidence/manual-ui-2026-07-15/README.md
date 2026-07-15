# LOB Arena manual UI evidence — 2026-07-15

This sanitized bundle records two workflows started manually from the Nebius Control Panel. It separates completed cloud evidence from submitted or locally completed stages so that the article does not overstate execution status.

## Completed managed experiment

Experiment `EXP-84D07DB1` completed as Nebius Serverless Job `aijob-e00bjapxe5debkqzt8`. The backend collected seven Job-output artifacts from Object Storage, normalized them into the experiment, and uploaded the associated evidence records to S3.

| Measure | Value |
|---|---:|
| Workloads / unique derived seeds | 100 / 100 |
| Difficulty mix | 20 easy, 50 medium, 20 hard, 10 adversarial |
| Scenario allocation | 20 each across four attacks plus normal control |
| Order-book events | 12,414 |
| Labels / raw alert records | 100 / 61 |
| Job lifecycle | 159.800 s |
| Matched confusion counts | TP 60, FN 20, FP 0, TN 20 |
| Precision / recall / F1 | 1.000 / 0.750 / 0.857 |
| Normal-control specificity / FPR | 1.000 / 0.000 |

Spoofing-like Wall, Layering-like Pattern, and Quote Stuffing Burst each reached 20/20 matched detections. Liquidity Evaporation produced 20 false negatives and recall 0.0. The committed [detector metrics](detector_metrics.csv) preserve the per-scenario result.

The empty `trades.jsonl` in this run is a known evidence boundary: these figures validate the synthetic order-book event and detector path, not a trade-based benchmark. They are not a claim of real-market surveillance accuracy.

## Real Endpoint activity from the UI session

The same UI window generated 12 real requests to the L40S/vLLM Endpoint:

| Operation | Calls |
|---|---:|
| Market-abuse scenario generation | 2 |
| Event explanation | 1 |
| Investigation Team | 2 |
| Investigation report | 7 |
| **Total** | **12** |

All 12 calls completed with `Qwen/Qwen2.5-14B-Instruct`, `model_mode=local_vllm`, no fallback, and an S3-uploaded request/response/metadata evidence record. They used 11,246 prompt tokens and 5,033 completion tokens (16,279 total), with mean latency 17.608 s and P50 latency 14.805 s. Both Investigation Team responses contain a non-empty, schema-validated `structured_assessment`; the seven benchmark investigations returned structured JSON reports.

## Polished E2E status boundary

The manual Polished E2E workflow `EXP-E88FB504` completed its scenario generation, simulation, alert, explanation, Investigation Team, local nine-replay tournament, and eight-artifact evidence packaging. It used three of the Endpoint calls above, 5,017 tokens, 20 simulation events, and uploaded evidence record `EVD-E0E6EE5E2B40` to S3.

Its submitted cloud tournament child remained unresolved after the status lookup returned `NotFound`; therefore this bundle does **not** claim that child as a completed cloud Job. The independently submitted managed experiment `EXP-84D07DB1` is the completed Job evidence for this UI session.

No credential, bearer token, signed URL, Object Storage key, private hostname, Endpoint URL, or raw environment-specific log is included.
