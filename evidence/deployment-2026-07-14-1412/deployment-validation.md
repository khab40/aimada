# Deployment validation

Validated `2026-07-14T14:23:13Z` against the configured production Nebius Endpoint. Git HEAD: `dadf19d` (the working tree also contains the release-freeze changes).

| Check | Result | Evidence |
|---|---|---|
| Endpoint health | PASS | `/health` returned `status=ok`; `/ready` returned `status=ready`; both reported `endpoint_mode=model_mode=local_vllm` and `Qwen/Qwen2.5-14B-Instruct`. |
| vLLM startup | PASS | Production logs show CUDA detection, vLLM `0.10.1.1`, one-GPU engine initialization, API-server startup, and readiness. Active settings: `bfloat16`, 16,384-token context, prefix caching, and 16 maximum sequences. |
| GPU memory | PASS | vLLM reported `27.5681 GiB` for model loading, `12.03 GiB` available for KV cache, and a 65,680-token GPU KV cache. |
| Order-book inference | PASS | HTTP 200; 22.945s end-to-end and 22.621s model latency; four evidence reasons; `fallback_reason=null`. |
| Investigation report | PASS | HTTP 200; 18.286s end-to-end and 17.959s model latency; structured findings, limitations, actions, summary, and disclaimer; `fallback_reason=null`. |
| Structured JSON | PASS | Response field types matched the endpoint contracts: strings for narrative fields and arrays for findings, timeline, limitations, and recommended actions. |
| Prompt layer | PASS | All 7 prompt/schema/example tests passed. Live spoofing input produced metric-specific evidence and a spoofing-like classification through Qwen, not the deterministic fallback. |

GPU figures are vLLM startup allocations, not an instantaneous `nvidia-smi` sample. Latencies are representative single-request measurements, not a throughput benchmark. Results cover synthetic educational scenarios only and are unsuitable for real surveillance or compliance decisions.
