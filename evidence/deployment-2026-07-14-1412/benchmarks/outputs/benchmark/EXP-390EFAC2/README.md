# AIMADA jury evidence: `EXP-390EFAC2`

This is a sanitized, commit-safe export from the local AIMADA backend after artifacts were collected from Nebius Object Storage. Raw credentials, authorization headers, endpoint hostnames, and duplicate raw model responses are excluded.

- Experiment status: `completed`
- Requested workloads: 100
- Workload labels retained: 100
- Normalized attacks represented in aggregate metrics: 80
- Normal/control rows: 20 `normal_market` rows with `has_attack:false`
- Completed Nebius Serverless Jobs: 2 (`aijob-e00cygzs8f63h4dg2z`, `aijob-e00qq10wjz0p5karsp`)
- Successful Nebius Endpoint investigations: 7
- Completed, S3-uploaded evidence records in this run window: 11 (8 endpoint calls)
- Run window: `2026-07-13T14:43:13.934938+00:00` to `2026-07-13T15:00:06.864739+00:00`

The difference between requested workloads and normalized attacks is a denominator distinction, not data loss. `labels.jsonl` contains 20 rows each for `normal_market`, `spoofing_like`, `layering_like`, `quote_stuffing`, and `liquidity_evaporation`; the aggregate attack count excludes the 20 benign `normal_market` controls, and detector metrics normalize `liquidity_evaporation` to `pump_and_cancel`.

Metrics describe this synthetic benchmark only; they do not demonstrate real-market surveillance accuracy and must not be used for compliance or trading decisions.

Verify integrity with `sha256sum -c checksums.sha256` from this directory. Regenerate with:

```bash
python3 scripts/export_jury_evidence.py --experiment-id EXP-390EFAC2
```
