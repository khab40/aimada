# Benchmark evidence index

Only curated evidence under this directory is allowed into Git; all other generated `outputs/` content remains ignored.

- [`EXP-390EFAC2`](EXP-390EFAC2/README.md): completed 100-workload managed experiment, including 80 labeled attack rows, 20 normal-market control rows, two completed Serverless Job records, seven AI investigations, S3 evidence metadata, reports, and checksums.

The export intentionally excludes credentials, authorization values, endpoint hostnames, raw Job logs, and duplicate raw model responses. Runtime and cost values are summarized in the judge-facing submission index; sanitized UI screenshots live under `assets/screenshots/`.

Regenerate from a running backend with `python3 scripts/export_jury_evidence.py --experiment-id EXP-390EFAC2`.
