# Architecture Records

This folder contains Architecture Record Documents (ARDs) for Nebius Market Abuse Arena.

ARDs capture architecture decisions, context, tradeoffs, implementation phases, and links to supporting documentation. They are meant to complement the higher-level architecture overview in [../architecture.md](../architecture.md).

## Records

### Core System Design

- [ARD-0001: Overall Architecture](ARD-0001-overall-architecture.md) — System-wide architecture: interactive path, batch path, and component responsibilities
- [ARD-0002: WebSocket State Schema](ARD-0002-websocket-state-schema.md) — Real-time state messaging format for live arena updates

### Detector & Evidence Design

- [ARD-0003: Detector Evidence Model](ARD-0003-detector-evidence-model.md) — How detectors encode findings and confidence scores
- [ARD-0006: Scenario Labeling and Reproducibility](ARD-0006-scenario-labeling-and-reproducibility.md) — Ground-truth labeling for benchmark validation

### Data & Artifacts

- [ARD-0004: Benchmark Artifact Format](ARD-0004-benchmark-artifact-format.md) — Persisted data formats (JSON, Parquet, CSV, Markdown)

### Nebius Integration

- [ARD-0005: Nebius Endpoint Contract](ARD-0005-nebius-endpoint-contract.md) — API contracts for incident explanations and scenario generation
- [ARD-0007: Nebius Serverless AI Jobs](ARD-0007-nebius-serverless-ai-jobs.md) — Batch job execution for benchmarks and dataset generation
- [ARD-0008: Nebius Serverless AI Endpoints](ARD-0008-nebius-serverless-ai-endpoints.md) — Interactive serverless AI endpoint integration
- [ARD-0009: Judge Mode Investigation Reports](ARD-0009-judge-mode-investigation-reports.md) — Investigation and report generation workflows

## ARD Format

Each ARD includes:

| Section | Purpose |
|---------|---------|
| **Status** | Accepted, Proposed, Rejected, Superseded |
| **Date** | When the record was written |
| **Context** | Business and technical background |
| **Decision** | What was decided and why |
| **Architecture** | Diagrams and component overview |
| **Implementation Impact** | How the decision affects development |
| **Alternatives Considered** | Rejected approaches and rationale |
| **Consequences** | Tradeoffs and implications |
| **Related Documentation** | Links to supporting docs and other ARDs |

## How to Use ARDs

1. **Understand a design decision**: Find the relevant ARD and read the Context → Decision → Consequences sections
2. **Implement a feature**: Check which ARDs apply, review implementation impact
3. **Make a new decision**: Use an ARD as a template (copy an existing one and follow the format)
4. **Trace architecture lineage**: Links in "Related Documentation" connect ARDs and other documents

## Workflow & Traceability

All ARDs are linked in the main [Architecture](../architecture.md) document and in [Use Cases](../USE_CASES.md) to show which decisions support which workflows.

This ensures:
- ✓ No stale decisions (ARDs are always referenced)
- ✓ Clear traceability (decisions → implementation → workflows)
- ✓ Single source of truth (decisions recorded in ARDs, not scattered in comments)
