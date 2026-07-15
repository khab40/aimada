# LOB Arena production Endpoint evidence — 2026-07-15

This sanitized evidence set records 25 completed calls to Nebius Serverless AI Endpoint `aiendpoint-e00hx85p86yrb7w7jn` on `gpu-l40s-d`, preset `1gpu-16vcpu-96gb`, using `Qwen/Qwen2.5-14B-Instruct` through local vLLM.

| Route | Calls | Contract |
|---|---:|---|
| AI Investigation Team | 17 | Professional surveillance request schema and validated structured assessment |
| Investigation Report | 4 | Schema-bearing surveillance prompt and JSON report response |
| Market-abuse Scenario Generator | 4 | Bounded scenario request and JSON narrative response |
| **Total** | **25** | **25 real vLLM responses; zero fallbacks** |

## Measured usage

| Measure | Value |
|---|---:|
| Prompt tokens | 25,084 |
| Completion tokens | 13,345 |
| Total tokens | 38,429 |
| Mean Endpoint latency | 24.038 s |
| P50 Endpoint latency | 27.141 s |
| Minimum / maximum latency | 4.382 s / 31.347 s |
| S3-uploaded evidence records | 25 / 25 |
| Sanitized request/response artifact bytes | 239,918 |

The 17 Investigation Team responses all contain a non-empty `structured_assessment`, report `model_mode=local_vllm`, include token usage, and have no fallback reason. The request path embeds `SurveillanceInvestigationResponse.model_json_schema()` in the vLLM user payload; the OpenAI-compatible call requests `response_format={"type":"json_object"}`; the response is Pydantic-validated before being preserved in the API result.

All four implemented scenario families are represented in each repeated set: Spoofing-like Wall, Layering-like Pattern, Quote Stuffing Burst, and Liquidity Evaporation. Payloads use medium difficulty, varied synthetic ticks, agents, order-book context, trades, detector scores, and market metrics.

Every call produced a local request/response/metadata bundle, an evidence index row, and an uploaded S3 evidence prefix. Representative canary evidence: `EVD-C45A179D2DA4` (1,850 tokens, 30.462 s, S3 uploaded, structured response, no fallback). Pricing rates were not configured, so this evidence reports measured usage without fabricating a dollar cost.

No credential, authorization header, signed URL, Object Storage key, private hostname, or Endpoint token is included.
