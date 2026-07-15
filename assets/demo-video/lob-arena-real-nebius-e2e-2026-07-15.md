# LOB Arena real Nebius E2E recording guide

Target length: 4–5 minutes. Keep the runtime switch on **Nebius Cloud** and show the green service probes before starting.

## 1 · Runtime

Show Frontend, Backend, Runner, AI Endpoint, Jobs, and Storage as ready. State that the runner contains synthetic agents in a separate workspace, the Endpoint hosts Qwen2.5-14B through vLLM on one L40S, Jobs execute batch evaluation, and Object Storage preserves evidence.

## 2 · Scenario Generator

Select a medium or hard canonical scenario: Spoofing-like Wall, Layering-like Pattern, Quote Stuffing Burst, or Liquidity Evaporation. Generate it with the real Endpoint. Point out the `local_vllm` model mode, structured JSON response, token counts, and lack of fallback. Replay it in Arena and show advancing ticks, the synthetic LOB, agent activity, detector scores, and any incident.

## 3 · Investigation Team

Run the Investigation Team for the selected incident. Show classification, confidence, evidence, counter-evidence, recommended review actions, and consensus. Explain that deterministic detectors create the alert; AI explains structured evidence and does not replace ground truth. Benchmark alert summaries are visible below **Explain benchmark alerts** on this tab.

Show the production Endpoint evidence set: 25 real L40S/vLLM calls, 38,429 tokens, zero fallbacks, 25 S3 uploads, and 17/17 validated structured Investigation Team responses. Open one response artifact and show `model_mode=local_vllm`, token usage, and the preserved `structured_assessment`.

## 4 · Detector Tournament

Open one of the six corrected 200-workload experiments. Show the five workloads, base seed, Nebius Job ID, completed state, leaderboard, and aggregate metrics. Report the full production set: 1,200 unique run seeds, 148,958 events, TP 710, FN 250, FP 0, TN 240, precision 1.000, recall 0.740, and F1 0.850. Explicitly show the Liquidity Evaporation recall of 0.0 as the benchmark finding.

## 5 · Execution Trace

Show the execution graph and Usage and Cost Monitor: six jobs, 1,200 workloads, 148,958 events, 1,308.436 seconds of measured lifecycle, 25 Endpoint calls, 38,429 Endpoint tokens, 25 Endpoint S3 records, and 42 synchronized Job outputs. Show that all six event and metrics digests differ and the 1,200 derived seeds have zero overlap. State that pricing rates are not configured, so no dollar amount is fabricated. Open the professional artifact cards for metrics, reports, manifests, logs, structured responses, and cloud evidence.

Use the completed manual experiment `EXP-84D07DB1` for the publication take: show 100 workloads, 100 unique seeds, 12,414 events, TP 60, FN 20, FP 0, TN 20, and F1 0.857. Open the seven AI investigation reports and the S3-synchronized artifact cards. Do not present `EXP-E88FB504` as a completed cloud Job: its local Polished E2E stages completed, but its cloud child lookup returned `NotFound`.

Safety line: LOB Arena is a synthetic educational benchmark. It uses no real orders, provides no trading signals, and is not suitable for compliance decisions.
