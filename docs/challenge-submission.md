# Challenge Submission

## Submission links

- **Repository:** [github.com/khab40/aimada](https://github.com/khab40/aimada)
- **Technical article:** [Technical article draft](linkedin-technical-blog-post.md) — publication URL not yet available.
- **Video:** Rendered demo not yet published; [narration script](../assets/demo-video/ai-market-abuse-detection-arena-ceo-demo-script2.txt) and [captions](../assets/demo-video/ai-market-abuse-detection-arena-ceo-demo-captions.srt) are included.
- **Challenge category:** Nebius Serverless AI Builders Challenge.
- **Hashtag:** `#NebiusServerlessChallenge`

## One-minute summary

AIMADA is a synthetic market-surveillance arena that makes order-book abuse-like behavior visible, measurable, and explainable without using real trading data. A FastAPI/React application runs deterministic spoofing, layering, quote-stuffing, and liquidity-shock scenarios; rule-based detectors generate evidence; and Nebius AI turns that evidence into investigation reports. Interactive inference is assigned to a Serverless Endpoint, while repeatable detector tournaments are assigned to Serverless Jobs. The result is an inspectable workflow from labeled scenario through alert, explanation, metrics, leaderboard, report, and charts. AIMADA is an educational benchmark and research scaffold, not a production compliance or trading system.

## Nebius Serverless usage

- **Endpoint:** Nebius H100 Serverless Endpoint (`gpu-h100`, `1gpu-16vcpu-200gb`) serving `Qwen/Qwen2.5-1.5B-Instruct` through local vLLM for investigation reports, alert explanations, and scenario generation. See [deployment configuration](nebius-deployment.md#nebius-ai-endpoints).
- **Job:** Nebius Serverless Job using the repository jobs image and the CPU `cpu-d3`, `4vcpu-16gb` preset for parallel simulations, detector evaluation, aggregation, and artifact generation. See [job configuration](../serverless/jobs/job_config.example.yaml).
- **Why each execution model was selected:** Endpoint requests are short, interactive, and latency-sensitive. Tournament runs are finite, parallel, reproducible batch workloads that should terminate after persisting metrics and reports.

## Reproduction

- **Local path:** Follow the four commands in [Getting Started](../README.md#getting-started), then open `http://localhost:5173` and run the Serverless E2E demo. Generated evidence is written under `outputs/serverless-smoke/`.
- **Real Nebius path:** Build and push both images, deploy the endpoint, create the job, and run the smoke workflow using [Nebius deployment instructions](nebius-deployment.md). Cloud completion must be confirmed by job status and collected artifacts; submission alone is not treated as success.
- **Runtime:** Local stack setup and mock demo typically take 3–5 minutes. The recorded local 10-scenario tournament ran from `2026-07-12T09:16:37.778151Z` to `2026-07-12T09:16:38.492110Z` (0.714 s, excluding container startup). Production jobs completed successfully, but no consolidated cloud runtime summary is checked in, so this document does not invent one.
- **Cost:** Local mock execution costs $0 in cloud charges. A consolidated Nebius billing record is not checked in, so no cloud cost is claimed; published cost should be calculated from measured active time and the applicable billing record.

## Results

- **Number of runs:** More than ten production Serverless AI Job runs validated the batch workflow. The small local metric example contains 10 scenario executions: 5 each for `spoofing-like` and `layering-like`.
- **Best detector in the local example:** `layering_like`, with precision 1.0, recall 1.0, and F1 1.0 on the deliberately small layering-like sample.
- **Local example metrics:** Macro F1 0.125 across all scenario-detector pairs; 10 false positives; 5 false negatives; 500 ms average detection latency for detected layering cases.
- **Main finding:** Production runs validated container execution, scenario generation, detector evaluation, aggregation, reporting, logs, and artifact persistence. The local metrics validate integration and reproducibility only; they are too small and narrow to support a real-world accuracy claim.

## Proof of execution

- **Job ID/status screenshot:** More than ten production jobs completed successfully and are visible in Nebius production logs; a curated screenshot index is still publication work.
- **Endpoint screenshot:** A vLLM-backed endpoint executed scenario generation, incident analysis, investigation reporting, and structured market-event explanation routes; the curated screenshot link is still publication work.
- **Logs:** Production execution logs exist in Nebius. Redacted excerpts have not yet been committed; local runtime logs are generated under `outputs/`.
- **Output artifacts:** Production runs produced job artifacts, detector metrics, reports, and logs. The reproducible local tournament writes `metrics.csv`, `results.json`, `benchmark_report.md`, and charts under `outputs/nebius/tournaments/<id>/artifacts/`.

## Limitations

- Production execution is validated, but the repository still needs a compact redacted evidence bundle, consolidated runtime/cost summary, and direct console screenshot links.
- The rendered demo video and published article URL remain missing.
- Reported metrics come from 10 deterministic synthetic scenario executions and do not measure real-market surveillance performance.
- Results cover only spoofing-like and layering-like scenarios; broader scenarios, seeds, detectors, and a normal-market baseline are required before comparison claims are credible.
- The system is an educational research scaffold and must not be used for compliance decisions, trading signals, or allegations of market manipulation.
