# AIMADA jury evidence: `EXP-18E88EAF`

This is a sanitized, commit-safe export from the local AIMADA backend after artifacts were collected from Nebius Object Storage. Raw credentials, authorization headers, endpoint hostnames, and duplicate raw model responses are excluded.

- Experiment status: `completed`
- Requested workloads: 5
- Normalized attacks represented in aggregate metrics: 4
- Completed Nebius Serverless Jobs: 1 (`aijob-e00q7cdpz32jyk0bsg`)
- Successful Nebius Endpoint investigations in this evidence bundle: 2 (`EVD-EA016D5A3647`, `EVD-DDB7E7683A8F`)
- Completed, S3-uploaded Job evidence records in the experiment run window: 3 (the Endpoint calls are recorded separately below)
- Run window: `2026-07-14T17:33:14.325268+00:00` to `2026-07-14T17:38:41.093677+00:00`

The difference between requested and normalized attacks is retained as evidence, not hidden. Metrics describe this synthetic benchmark only; they do not demonstrate real-market surveillance accuracy and must not be used for compliance or trading decisions.

The two sanitized Endpoint request/response pairs are `endpoint-spoofing-request.json`, `endpoint-spoofing-response.json`, `endpoint-layering-request.json`, and `endpoint-layering-response.json`. They were executed through the live backend proxy against the vLLM-backed production Endpoint; both returned `model_mode=local_vllm` with no fallback.

Verify integrity with `sha256sum -c checksums.sha256` from this directory. Regenerate with:

```bash
python3 scripts/export_jury_evidence.py --experiment-id EXP-18E88EAF
```
