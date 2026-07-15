# Challenge Submission

## Submission links

- **Repository:** [github.com/khab40/lob-arena](https://github.com/khab40/lob-arena)
- **Technical article:** [Technical article draft](linkedin-technical-blog-post.md) — publication URL not yet available.
- **Video:** Rendered demo not yet published; [narration script](../assets/demo-video/ai-market-abuse-detection-arena-ceo-demo-script2.txt) and [captions](../assets/demo-video/ai-market-abuse-detection-arena-ceo-demo-captions.srt) are included.
- **Challenge category:** Nebius Serverless AI Builders Challenge.
- **Hashtag:** `#NebiusServerlessChallenge`

## One-minute summary

LOB Arena is a synthetic market-surveillance arena that makes order-book abuse-like behavior visible, measurable, and explainable without using real trading data. A FastAPI/React application runs deterministic spoofing, layering, quote-stuffing, and liquidity-shock scenarios; rule-based detectors generate evidence; and Nebius AI turns that evidence into investigation reports. Interactive inference is assigned to a Serverless Endpoint, while repeatable detector tournaments are assigned to Serverless Jobs. The result is an inspectable workflow from labeled scenario through alert, explanation, metrics, leaderboard, report, and charts. LOB Arena is an educational benchmark and research scaffold, not a production compliance or trading system.

## Nebius Serverless usage

- **Endpoint:** The archived representative challenge run used a Nebius H100 Serverless Endpoint (`gpu-h100`, `1gpu-16vcpu-200gb`) with `Qwen/Qwen2.5-1.5B-Instruct`. The current right-sized deployment configuration uses one L40S (`gpu-l40s-g`) with `Qwen/Qwen2.5-14B-Instruct`; see [deployment configuration](nebius-deployment.md#nebius-ai-endpoints) and [migration notes](l40s-migration.md).
- **Job:** Nebius Serverless Job using the repository jobs image and the CPU `cpu-d3`, `4vcpu-16gb` preset for parallel simulations, detector evaluation, aggregation, and artifact generation. See [job configuration](../serverless/jobs/job_config.example.yaml).
- **Why each execution model was selected:** Endpoint requests are short, interactive, and latency-sensitive. Tournament runs are finite, parallel, reproducible batch workloads that should terminate after persisting metrics and reports.

## Reproduction

- **Local path:** Follow the four commands in [Getting Started](../README.md#getting-started), then open `http://localhost:5173` and run the Serverless E2E demo. Generated evidence is written under `outputs/serverless-smoke/`.
- **Real Nebius path:** Build and push both images, deploy the endpoint, create the job, and run the smoke workflow using [Nebius deployment instructions](nebius-deployment.md). Cloud completion must be confirmed by job status and collected artifacts; submission alone is not treated as success.
- **Runtime and cost:** Local stack setup and mock demo typically take 3–5 minutes. The recorded local 10-scenario tournament ran from `2026-07-12T09:16:37.778151Z` to `2026-07-12T09:16:38.492110Z` (0.714 s, excluding container startup). The production measurements below use checked-in evidence from `EXP-18E88EAF` and public Nebius list rates current at publication time; final billing can differ because Nebius rounds usage and excludes taxes.

| Workflow | Measured production evidence | Infrastructure | Runtime / latency | Approximate active compute cost | Output |
| --- | --- | --- | --- | ---: | --- |
| Local mock demo | Local deterministic path | Laptop, Docker Compose | 3-5 min including stack startup | $0 | Demo artifacts under `outputs/serverless-smoke/` |
| Serverless Job tournament | Job `aijob-e00q7cdpz32jyk0bsg`, experiment `EXP-18E88EAF` | Nebius Serverless Job, `cpu-d3`, `4vcpu-16gb`, image `ghcr.io/khab40/lob-arena-jobs:artifacts-v3-20260714-151355` | 5 scenarios in 181 s (`2026-07-14T17:33:35Z` to `2026-07-14T17:36:36Z`) | ~$0.005 using $0.10/hour CPU-only list pricing | Metrics, benchmark report, Job logs, and seven S3 artifacts synchronized to backend evidence |
| vLLM Endpoint representative calls | Endpoint EVDs `EVD-EA016D5A3647` and `EVD-DDB7E7683A8F` | Nebius Serverless Endpoint, `gpu-l40s-g`, `1gpu-16vcpu-200gb`, `Qwen/Qwen2.5-14B-Instruct`, vLLM | 2 structured investigation calls; P50 24.20 s, P95 28.78 s; 52.98 s combined active request latency | ~$0.023 using $1.55/GPU-hour L40S AMD list pricing for request-active time | Structured JSON investigation responses, Endpoint evidence records, S3 archival, backend sync, UI download links |

Rates are taken from the [Nebius public pricing page](https://nebius.com/prices): CPU-only AMD EPYC Genoa is listed from `$0.10/hour`, and NVIDIA L40S with AMD CPU is listed from `$1.55/GPU-hour`. The Endpoint cost above counts measured request latency only; it does not include idle warm time, startup time, storage, or any console-side rounding.

## Results

- **Number of runs:** More than ten production Serverless AI Job runs validated the batch workflow. The committed `EXP-390EFAC2` evidence requested and retained 100 workload labels: 80 labeled attack rows plus 20 `normal_market` control rows.
- **Best detector in the committed example:** The built-in deterministic detector suite reached precision/recall/F1 of 1.0 for the synthetic layering, quote-stuffing, and spoofing scenarios; recall was 0.0 for the normal-market and pump-and-cancel rows.
- **Endpoint investigations:** Seven reports completed in Nebius mode with no fallback; the evidence window contains eight completed, S3-uploaded Endpoint records.
- **Main finding:** Production runs validated container execution, scenario generation, detector evaluation, aggregation, reporting, logs, and artifact persistence. These synthetic metrics validate integration and reproducibility only; they do not support a real-world surveillance-accuracy claim.

### Workload-count reconciliation

The `EXP-390EFAC2` run did not drop 20 workloads. The checked-in `labels.jsonl` contains 100 rows: 20 `normal_market` controls with `has_attack:false`, plus 20 rows each for `spoofing_like`, `layering_like`, `quote_stuffing`, and `liquidity_evaporation`. The aggregate report's "80 attacks" denominator excludes the benign control rows by design. In detector metrics, `liquidity_evaporation` is normalized to the `pump_and_cancel` scenario row, so the five 20-row workload groups are represented as `normal_market`, `spoofing`, `layering`, `quote_stuffing`, and `pump_and_cancel`.

## Proof of execution

- **Job ID/status screenshot:** More than ten production jobs completed successfully and are visible in Nebius production logs; sanitized UI screenshots are listed in the [screenshot checklist](../assets/screenshots/README.md).
- **Endpoint screenshot:** A vLLM-backed endpoint executed scenario generation, incident analysis, investigation reporting, and structured market-event explanation routes; see the [runtime status screenshot](../assets/screenshots/Screenshot%202026-07-14%20at%2019.06.53.png) and [investigation screenshot](../assets/screenshots/Screenshot%202026-07-14%20at%2017.41.43.png).
- **Logs:** The sanitized [Nebius evidence index](../outputs/benchmark/EXP-18E88EAF/nebius_evidence_index.json) records completed Job operations whose evidence bundles were uploaded to S3. Raw logs remain excluded because they can contain environment-specific values.
- **Output artifacts:** The committed [benchmark evidence bundle](../outputs/benchmark/EXP-18E88EAF/README.md) includes job records, aggregate metrics, a detector/model leaderboard, Endpoint request/response examples, the benchmark report, a manifest, and SHA-256 checksums. The frozen `EXP-390EFAC2` evidence remains available under [deployment evidence](../evidence/deployment-2026-07-14-1412/benchmarks/outputs/benchmark/EXP-390EFAC2/README.md).
- **CI and secret scanning:** [GitHub Actions](../.github/workflows/ci.yml) runs backend, frontend, deterministic-evaluation, agent-workspace, Compose, image, and Gitleaks checks without building the long-running Nebius deployment images.

## Limitations

- Production execution is validated, compact redacted evidence bundles are committed, and the runtime/cost statement above records the measured cloud run used for publication. Private console screenshots are intentionally not required to reproduce the public evidence chain.
- The rendered demo video and published article URL remain missing.
- The committed 100-workload evidence contains 80 labeled attack rows and 20 normal-market control rows; this is a denominator distinction, not an unexplained data loss.
- Results cover five synthetic scenario labels with one deterministic detector suite/model dimension; broader seeds and learned-detector comparisons are required before comparative claims are credible.
- The system is an educational research scaffold and must not be used for compliance decisions, trading signals, or allegations of market manipulation.
