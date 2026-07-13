# Jury evidence index

Only curated evidence under this directory is allowed into Git; all other generated `outputs/` content remains ignored.

- [`EXP-390EFAC2`](EXP-390EFAC2/README.md): completed 100-workload managed experiment, including two completed Serverless Job records, 80 normalized metric rows, seven AI investigations, S3 evidence metadata, reports, and checksums.

The export intentionally excludes credentials, authorization values, endpoint hostnames, raw Job logs, and duplicate raw model responses. Console screenshots and billing records belong in the judge-facing submission index when available.

Regenerate from a running backend with `python3 scripts/export_jury_evidence.py --experiment-id EXP-390EFAC2`.
