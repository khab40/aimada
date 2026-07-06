# Serverless AI Endpoint

FastAPI container for Nebius Serverless AI Endpoint deployment.

It exposes the AI surfaces used by the backend:

- `GET /health`
- `POST /orderbook-alert`
- `POST /investigation-team`
- `POST /investigation-report`
- `POST /explain-event`
- `POST /explain-simulation`
- `POST /generate-report`
- `POST /generate-incident-report`
- `POST /generate-scenario`
- `POST /generate-smart-scenario`
- `POST /generate-market-abuse-scenario`

## Modes

- `NEBIUS_ENDPOINT_MODE=mock` returns deterministic structured responses.
- `NEBIUS_ENDPOINT_MODE=ai` calls Nebius through an OpenAI-compatible
  chat completions request.

Required for AI mode:

```bash
NEBIUS_API_KEY=...
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
NEBIUS_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

Existing deployments can keep using `NEBIUS_AI_STUDIO_BASE_URL` and `NEBIUS_AI_MODEL`; the endpoint treats them as backward-compatible aliases when the new names are unset.

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

Generate canonical market-abuse scenario:

```bash
curl -X POST http://localhost:9000/generate-market-abuse-scenario \
  -H 'Content-Type: application/json' \
  -d '{
    "manipulation_type":"spoofing",
    "difficulty":"medium",
    "symbol":"AIMD",
    "duration_ticks":120,
    "liquidity_regime":"thin",
    "volatility_regime":"high",
    "seed":42
  }'
```

Score an order-book window:

```bash
curl -X POST http://localhost:9000/orderbook-alert \
  -H 'Content-Type: application/json' \
  -d '{
    "bids":[{"price":68120,"quantity":12.4,"owner":"abuser"}],
    "asks":[{"price":68130,"quantity":1.8,"owner":"normal"}],
    "features":{"wall_size_ratio":8.2,"message_rate":21,"cancel_to_trade_ratio":5.4},
    "scenario_hint":"spoofing"
  }'
```

## Backend Wiring

After deployment, set backend env:

```bash
NEBIUS_ENDPOINT_BASE_URL=http://<endpoint>
# Optional per-route overrides:
NEBIUS_INCIDENT_EXPLAINER_URL=http://<endpoint>/explain-event
NEBIUS_SCENARIO_GENERATOR_URL=http://<endpoint>/generate-scenario
NEBIUS_MARKET_ABUSE_SCENARIO_URL=http://<endpoint>/generate-market-abuse-scenario
NEBIUS_ORDERBOOK_ALERT_URL=http://<endpoint>/orderbook-alert
NEBIUS_INVESTIGATION_REPORT_URL=http://<endpoint>/investigation-report
NEBIUS_API_KEY=<optional endpoint token>
```

## Docker

```bash
docker build -f serverless/endpoint/Dockerfile -t nebius-market-abuse-endpoint serverless/endpoint
docker run --rm -p 9000:9000 nebius-market-abuse-endpoint
```
