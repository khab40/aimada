# Serverless AI Endpoint

FastAPI container for Nebius Serverless AI Endpoint deployment.

It exposes the AI surfaces used by the backend:

- `GET /health`
- `POST /explain-event`
- `POST /explain-simulation`
- `POST /generate-report`
- `POST /generate-incident-report`
- `POST /generate-scenario`

## Modes

- `NEBIUS_ENDPOINT_MODE=mock` returns deterministic structured responses.
- `NEBIUS_ENDPOINT_MODE=ai` calls Nebius AI Studio through an OpenAI-compatible
  chat completions request.

Required for AI mode:

```bash
NEBIUS_API_KEY=...
NEBIUS_AI_STUDIO_BASE_URL=https://api.studio.nebius.com/v1
NEBIUS_AI_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

## Local Run

```bash
uvicorn app:app --host 0.0.0.0 --port 9000
```

Health:

```bash
curl http://localhost:9000/health
```

Explain incident:

```bash
curl -X POST http://localhost:9000/explain-event \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id":"INC-000001",
    "title":"Quote Stuffing detected",
    "type":"quote_stuffing",
    "agent":"ABUSER_01",
    "confidence":0.91,
    "severity":"High",
    "evidence":[
      {"key":"message_rate","label":"Message rate","value":42,"unit":"events/sec"}
    ],
    "replay":{"market":{"mid":68125,"spread":2}}
  }'
```

Generate scenario:

```bash
curl -X POST http://localhost:9000/generate-scenario \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Generate a bounded quote-stuffing red-team scenario.",
    "constraints":{
      "scenario_family":"quote_stuffing",
      "market_regime":"volatile",
      "goal":"hard_to_detect"
    }
  }'
```

## Backend Wiring

After deployment, set backend env:

```bash
NEBIUS_INCIDENT_EXPLAINER_URL=http://<endpoint>/explain-event
NEBIUS_SCENARIO_GENERATOR_URL=http://<endpoint>/generate-scenario
NEBIUS_API_KEY=<optional endpoint token>
```

## Docker

```bash
docker build -f serverless/endpoint/Dockerfile -t nebius-market-abuse-endpoint serverless/endpoint
docker run --rm -p 9000:9000 nebius-market-abuse-endpoint
```
