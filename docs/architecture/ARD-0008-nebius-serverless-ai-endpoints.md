# ARD-0008: Nebius Serverless AI Endpoints

Status: Accepted

Date: 2026-06-02

## Context

Live Arena Mode and Judge Mode need low-latency AI assistance without exposing
Nebius endpoint URLs or API tokens to the browser. The backend should send
structured, bounded evidence to Nebius and receive structured outputs that the
UI can render safely.

The endpoint path is not responsible for detector decisions. Deterministic
detectors create incidents and evidence first; the AI endpoint explains,
narrates, or formats that evidence.

## Decision

Use Nebius Serverless AI Endpoints for interactive AI requests:

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

The FastAPI backend is the integration boundary. It reads endpoint URLs and
optional tokens from environment variables, shapes request payloads, handles
timeouts, and falls back to typed mock responses when endpoints are not
configured.

## Endpoint Flow

```mermaid
graph TD
    UI["1. React UI posts /api/incidents/id/explain"]
    API["2. FastAPI backend receives request"]
    Store["3. Incident store loads evidence"]
    Nebius["4. Backend posts structured evidence to Nebius"]
    Explanation["5. Nebius returns typed explanation JSON"]
    Render["6. UI renders risk, summary, evidence bullets, action"]

    UI --> API
    API --> Store
    Store --> Nebius
    Nebius --> Explanation
    Explanation --> Render
```

## Endpoint Responsibilities

The endpoints support:

- incident explanation from detector evidence
- selected timeline segment explanation for Judge Mode
- scenario narration for demo playback
- bounded red-team scenario draft generation

They do not:

- inspect live market data directly
- decide whether manipulation occurred in real markets
- provide trading signals
- make compliance decisions

## Environment Contract

Endpoint wiring is controlled by environment variables:

```text
NEBIUS_INCIDENT_EXPLAINER_URL
NEBIUS_SCENARIO_GENERATOR_URL
NEBIUS_API_KEY optional
NEBIUS_TENANT_ID optional metadata/status field
```

Secrets must not be committed. The UI never receives the API key.

## Component Diagram

```mermaid
graph LR
    UI["React UI - Arena, Judge, Lab"]
    Backend["FastAPI Backend - Nebius client abstraction"]
    Explain["Incident explainer endpoint"]
    Scenario["Scenario generator endpoint"]
    Mock["Typed mock fallback"]

    UI --> Backend
    Backend --> Explain
    Backend --> Scenario
    Backend -.-> Mock
    Mock --> Backend
    Explain --> Backend
    Scenario --> Backend
    Backend --> UI
```

## Consequences

Positive:

- Secrets remain server-side.
- UI receives stable response shapes.
- Local development works without deployed Nebius endpoints.
- AI output remains grounded in deterministic detector evidence.

Tradeoffs:

- Endpoint schema changes require backend client updates.
- Timeout and fallback behavior must be visible in the UI.
- Generated narration must preserve educational safety framing.

## Related Documentation

- `docs/nebius-deployment.md`
- `serverless/endpoint/README.md`
- [ARD-0003: Detector Evidence Model](ARD-0003-detector-evidence-model.md)
- [ARD-0005: Nebius Endpoint Contract](ARD-0005-nebius-endpoint-contract.md)
