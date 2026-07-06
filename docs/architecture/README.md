# Architecture Records

This folder contains Architecture Record Documents (ARDs) for AI Market Abuse Detection Arena.

ARDs capture architecture decisions, context, tradeoffs, implementation phases, and links to supporting documentation. They are meant to complement the higher-level architecture overview in [../architecture.md](../architecture.md).

## Implementation Summary

Status as of 2026-07-06:

| ARD | Implementation | Notes |
|-----|----------------|-------|
| [ARD-0001](ARD-0001-overall-architecture.md) | `[partial]` | Real archived Nebius endpoint/job run is still missing |
| [ARD-0002](ARD-0002-websocket-state-schema.md) | `[done]` | Optional exported JSON schema and load-test throttling |
| [ARD-0003](ARD-0003-detector-evidence-model.md) | `[done]` | Broader threshold calibration against historical-style replay datasets |
| [ARD-0004](ARD-0004-benchmark-artifact-format.md) | `[partial]` | Run-specific canonical path and schema versioning are not complete |
| [ARD-0005](ARD-0005-nebius-endpoint-contract.md) | `[partial]` | Contract not yet proven with archived real endpoint execution |
| [ARD-0006](ARD-0006-scenario-labeling-and-reproducibility.md) | `[partial]` | Live label finalization and full event/order ID linkage remain incomplete |
| [ARD-0007](ARD-0007-nebius-serverless-ai-jobs.md) | `[partial]` | Real Serverless AI Job run and observability evidence are missing |
| [ARD-0008](ARD-0008-nebius-serverless-ai-endpoints.md) | `[partial]` | Real deployed endpoint logs, latency metrics, and screenshots are missing |
| [ARD-0009](ARD-0009-judge-mode-investigation-reports.md) | `[partial]` | Dedicated Judge Mode timeline selector is not fully implemented |
| [ARD-0010](ARD-0010-agent-runner-execution.md) | `[done]` | Auth/signing and durable transport for remote runners are future work |
| [ARD-0011](ARD-0011-exchange-liquidity-invariant.md) | `[done]` | Dynamic reference-price tracking and UI tuning are future work |
| [ARD-0012](ARD-0012-google-authentication.md) | `[done]` | Refresh tokens, revocation, asymmetric signing, and external secret management are future work |
| [ARD-0013](ARD-0013-ui-shell-preferences.md) | `[done]` | Screenshot capture and broader light-mode chart tuning are future work |
| [ARD-0014](ARD-0014-multiuser-platform-foundation.md) | `[partial]` | Durable backend workspace/case/audit tables and assignment APIs are future work |
| [ARD-0015](ARD-0015-nebius-ai-investigation-team.md) | `[done]` | Investigation endpoint is the primary interactive Nebius AI Serverless workflow |
| [ARD-0016](ARD-0016-ai-scenario-generator.md) | `[done]` | Scenario generation endpoint produces simulator-compatible AI Scenario Generator workloads |
| [ARD-0017](ARD-0017-ai-detector-tournament.md) | `[done]` | Serverless Jobs contract and local fallback power the AI Detector Tournament workflow |

Current UI architecture note: the product shell now exposes AI Command Center, Arena / Workload Generator, and Docs / Demo as the primary demo destinations. Scenario setup, incidents, investigations, detector tournaments, deployment status, and experiment artifacts are folded into the AI Command Center or linked from the active workflow. The About and ARD-0001 diagrams document the four execution areas: Front, Back, Agent Runners Workspace, and Nebius Serverless Cloud.

## Records

### Core System Design

- [ARD-0001: Overall Architecture](ARD-0001-overall-architecture.md) — System-wide architecture: interactive path, batch path, and component responsibilities
- [ARD-0002: WebSocket State Schema](ARD-0002-websocket-state-schema.md) — Real-time state messaging format for live arena updates

### Detector & Evidence Design

- [ARD-0003: Detector Evidence Model](ARD-0003-detector-evidence-model.md) — How detectors encode findings and confidence scores
- [ARD-0006: Scenario Labeling and Reproducibility](ARD-0006-scenario-labeling-and-reproducibility.md) — Ground-truth labeling for benchmark validation

### Data & Artifacts

- [ARD-0004: Benchmark Artifact Format](ARD-0004-benchmark-artifact-format.md) — Persisted data formats (JSON, Parquet, CSV, Markdown)

### Agent Execution

- [ARD-0010: Agent Runner Execution Architecture](ARD-0010-agent-runner-execution.md) — Local, remote, heavy, and LangGraph-compatible agent execution
- [ARD-0011: Exchange Liquidity Invariant And Agent Quote Ownership](ARD-0011-exchange-liquidity-invariant.md) — Baseline ladder guard and additive per-agent quote ownership

### Authentication

- [ARD-0012: Google Authentication And App Sessions](ARD-0012-google-authentication.md) — Google ID token verification, SQLite user storage, and app JWT sessions
- [ARD-0014: Multiuser Platform Foundation](ARD-0014-multiuser-platform-foundation.md) — Users, workspaces, roles, case ownership, report attribution, and audit trail model

### UI Shell And Presentation

- [ARD-0013: UI Shell Preferences And Demo Presentation](ARD-0013-ui-shell-preferences.md) — Banner asset, theme preference, collapsible auth widget, compact navigation, and paused-state-stable visualizations

### Nebius Integration

- [ARD-0005: Nebius Endpoint Contract](ARD-0005-nebius-endpoint-contract.md) — API contracts for incident explanations and scenario generation
- [ARD-0007: Nebius Serverless AI Jobs](ARD-0007-nebius-serverless-ai-jobs.md) — Batch job execution for benchmarks and dataset generation
- [ARD-0008: Nebius Serverless AI Endpoints](ARD-0008-nebius-serverless-ai-endpoints.md) — Interactive serverless AI endpoint integration
- [ARD-0009: Judge Mode Investigation Reports](ARD-0009-judge-mode-investigation-reports.md) — Investigation and report generation workflows
- [ARD-0015: Nebius AI Investigation Team](ARD-0015-nebius-ai-investigation-team.md) — Phase 1 build plan and implementation record for AI investigation via Nebius AI Serverless Endpoint
- [ARD-0016: AI Scenario Generator](ARD-0016-ai-scenario-generator.md) — Phase 2 build plan and implementation record for scenario generation via Nebius AI Serverless Endpoint
- [ARD-0017: AI Detector Tournament](ARD-0017-ai-detector-tournament.md) — Phase 3 build plan and implementation record for detector tournaments via Nebius Serverless Jobs

### Build Plan And Use Cases

- [Nebius AI Serverless Build Plan](../nebius-serverless-build-plan.md) — Three-phase implementation plan centered on Nebius execution
- [Nebius Serverless Use Cases](../use-cases/nebius-serverless-use-cases.md) — Product use cases and concrete API flows

## ARD Format

Each ARD includes:

| Section | Purpose |
|---------|---------|
| **Status** | Accepted, Proposed, Rejected, Superseded |
| **Date** | When the record was written |
| **Implementation Status** | What has landed and what is still missing |
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
