# ARD-0005: Nebius Endpoint Contract

Status: Accepted

Date: 2026-06-01

## Context

The backend needs AI-generated explanations for detected synthetic incidents and simulation summaries. The UI should not call Nebius directly. The backend should pass structured detector evidence to the serverless endpoint and receive structured response fields that can be stored and rendered.

## Decision

Expose Nebius Serverless AI Endpoints with explicit health, event explanation, simulation explanation, report-generation, and bounded scenario-generation routes.

Endpoint roles:

```mermaid
graph TD
    Endpoints["Nebius Serverless AI Endpoints"]
    Judge["Real-time AI judge"]
    Explain["Explanation generation"]
    Narrator["Scenario narrator"]

    Endpoints --> Judge
    Endpoints --> Explain
    Endpoints --> Narrator
```

Routes:

- `GET /health`
- `POST /explain-event`
- `POST /explain-simulation`
- `POST /generate-report`
- `POST /generate-scenario`

The endpoint accepts structured JSON evidence and returns structured JSON explanation output.

## Endpoint Flow

```mermaid
graph TD
    UI["1. React UI requests incident explanation"]
    Backend["2. FastAPI backend receives request"]
    StoreLoad["3. Backend loads incident evidence"]
    Endpoint["4. Backend posts to Nebius endpoint"]
    Response["5. Endpoint returns structured explanation"]
    StoreReport["6. Backend persists generated report"]
    UIResponse["7. UI renders title, risk, summary, evidence, action"]

    UI --> Backend
    Backend --> StoreLoad
    StoreLoad --> Endpoint
    Endpoint --> Response
    Response --> StoreReport
    StoreReport --> UIResponse
```

## Contract Diagram

```mermaid
graph TD
    IncidentRequest["ExplainIncidentRequest - id, type, confidence, severity, evidence, features"]
    SimulationRequest["ExplainSimulationRequest - simulation id, tick window, detector summary, incidents"]
    Explanation["ExplanationResponse - title, risk, summary, evidence, action, disclaimer"]
    ScenarioRequest["ScenarioGenerationRequest - prompt and constraints"]
    ScenarioResponse["ScenarioGenerationResponse - type, title, description, parameters, risk, safety note"]

    IncidentRequest --> Explanation
    SimulationRequest --> Explanation
    ScenarioRequest --> ScenarioResponse
```

## Response Requirements

The endpoint response must include:

- `title`
- `risk_level`
- `plain_english_summary`
- `evidence`
- `recommended_action`
- `disclaimer`

The disclaimer must preserve the project framing: educational simulation only, no real manipulation detection, no trading signals, and no compliance decisions.

## Environment Variables

The backend reads endpoint wiring from:

- `NEBIUS_INCIDENT_EXPLAINER_URL`
- `NEBIUS_SCENARIO_GENERATOR_URL`
- `NEBIUS_API_KEY` optional
- `NEBIUS_TENANT_ID` optional metadata/status field

## Consequences

Positive:

- UI remains decoupled from Nebius credentials and endpoint details.
- Explanations are grounded in deterministic detector evidence.
- Reports can be persisted with clear schema.

Tradeoffs:

- Backend must handle endpoint failures gracefully.
- Endpoint contract changes require backend and UI updates.
- Generated summaries still require safety framing and review.

## Related Documentation

- `docs/nebius-deployment.md`
- `serverless/endpoint/README.md`
- [ARD-0003: Detector Evidence Model](ARD-0003-detector-evidence-model.md)
- [ARD-0008: Nebius Serverless AI Endpoints](ARD-0008-nebius-serverless-ai-endpoints.md)
- [ARD-0009: Judge Mode Investigation Reports](ARD-0009-judge-mode-investigation-reports.md)
