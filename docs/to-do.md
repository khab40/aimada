# Todos left

## Evidence and correctness
DONE: Start real Nebius endpoint and jobs
Run several relatively heavy tasks from UI Control panel
DONE: Check results at Nebius cloud and grab results back to the project and repo

## Update documentation
LinkedIn, images suggested
Images and logs in Evidence.md


## Updates for Submission

## Video recording
Using transcript that already exists

## Suggestions from AI
Remaining publication work: Measured runtime/cost records and final Nebius/UI screenshots only.

# Codex Prompt 2 — Build the Judge-Facing Production Evidence Bundle

Create a compact, public, sanitized production-evidence bundle for the Nebius Serverless AI Builders Challenge.

The application already implements:

* more than ten successful Nebius Serverless AI Job runs;
* a vLLM-backed Nebius Serverless AI Endpoint;
* successful execution of multiple Endpoint routes;
* durable evidence archival to Nebius Object Storage;
* S3-to-backend synchronization;
* evidence display and download links in the UI.

Do not reimplement these features. Package existing evidence so judges can verify it quickly without access to private Nebius credentials or the private S3 bucket.

## Create this structure

```text
docs/evidence/
├── README.md
├── production-run-summary.md
├── endpoint/
│   ├── README.md
│   ├── endpoint-health-example.json
│   ├── endpoint-route-example.json
│   └── redacted-endpoint-log.txt
├── jobs/
│   ├── README.md
│   ├── production-run-index.json
│   ├── representative-job-status.json
│   └── redacted-job-log.txt
├── artifacts/
│   ├── manifest.json
│   ├── metrics.csv
│   ├── benchmark-report.md
│   └── artifact-index.json
└── screenshots/
    └── README.md
```

Use the actual existing output paths and names where appropriate rather than duplicating data unnecessarily.

## Requirements

1. Select one successful Serverless AI Job as the canonical representative production run.

2. Document:

* sanitized Job ID or shortened display form;
* final status;
* Job image and tag;
* hardware preset;
* scenario/run configuration;
* start and completion timestamps if available;
* measured runtime;
* produced artifacts;
* how evidence moved from Job execution to S3, backend storage and UI.

3. Include a small production-run history showing that more than ten runs completed.

4. Add Endpoint evidence for representative successful routes such as:

* health;
* scenario generation;
* incident analysis;
* investigation report;
* structured market-event explanation.

5. Preserve meaningful technical metadata:

* route name;
* status;
* latency;
* model;
* platform or hardware;
* execution timestamp.

6. Remove or redact:

* access keys;
* secret keys;
* bearer tokens;
* authorization headers;
* signed URLs;
* private endpoint hostnames where sensitive;
* tenant IDs;
* project IDs;
* personal email addresses;
* private local paths.

7. Never invent evidence, runtime, costs, IDs, metrics or screenshots.

8. When raw evidence is unavailable in the repository, create a clearly marked placeholder checklist in `docs/evidence/screenshots/README.md` rather than fabricating a result.

9. Update `docs/challenge-submission.md` so its Proof of Execution section contains direct relative links to this evidence bundle.

10. Add a prominent link near the top of the README:

```markdown
[Production Nebius evidence](docs/evidence/README.md)
```

## Evidence README structure

The judge-facing evidence README should include:

* what was executed;
* why Endpoints and Jobs were used;
* representative production Job;
* representative production Endpoint routes;
* S3 archival and synchronization flow;
* public sanitized artifacts;
* limitations;
* instructions for reproducing the local deterministic path.

## Validation

Run:

* secret scanning;
* tests for evidence archival and synchronization;
* any artifact validation scripts;
* Markdown checks if available.

Report:

* evidence files created;
* source artifacts used;
* all redactions applied;
* anything that still requires a manual screenshot.
