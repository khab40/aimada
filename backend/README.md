# Backend

FastAPI backend for the AI Market Abuse Detection Arena project.

The current runtime exposes a simple synthetic L2 order book simulation for the
arena UI. It ticks every 500 ms while running.

## Current Routes

- `GET /health`
- `GET /api/status`
- `GET /api/nebius/status`
- `POST /api/nebius/red-team-scenario`
- `POST /api/red-team/generate-scenario`
- `GET /api/arena/state`
- `POST /api/simulation/start`
- `POST /api/simulation/pause`
- `POST /api/simulation/reset`
- `POST /api/scenarios/spoofing-like`
- `POST /api/scenarios/layering-like`
- `POST /api/scenarios/quote-stuffing`
- `POST /api/scenarios/liquidity-evaporation`
- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `POST /api/incidents/{incident_id}/explain`
- `WS /ws/arena`

## Local Development

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/status
curl http://localhost:8000/api/nebius/status
curl http://localhost:8000/api/arena/state
curl -X POST http://localhost:8000/api/simulation/start
curl -X POST http://localhost:8000/api/simulation/pause
curl -X POST http://localhost:8000/api/simulation/reset
curl -X POST http://localhost:8000/api/scenarios/spoofing-like
curl -X POST http://localhost:8000/api/scenarios/layering-like
curl -X POST http://localhost:8000/api/scenarios/quote-stuffing
curl -X POST http://localhost:8000/api/scenarios/liquidity-evaporation
curl http://localhost:8000/api/incidents
curl http://localhost:8000/api/incidents/INC-000001
curl -X POST http://localhost:8000/api/incidents/INC-000001/explain
curl -X POST http://localhost:8000/api/red-team/generate-scenario \
  -H 'Content-Type: application/json' \
  -d '{"scenario_family":"quote_stuffing","market_regime":"volatile","goal":"hard_to_detect","constraints":{"max_duration_seconds":5}}'
curl -X POST http://localhost:8000/api/nebius/red-team-scenario \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"short spoofing-like wall in a thin book","constraints":{"scenario_type":"spoofing_like_wall"}}'
```

Nebius integration variables:

```bash
NEBIUS_TENANT_ID=your-tenant-id
NEBIUS_ENDPOINT_BASE_URL=https://your-nebius-endpoint
NEBIUS_API_KEY=optional-token
```

The backend derives `/explain-event` and `/generate-scenario` from `NEBIUS_ENDPOINT_BASE_URL`. You can still set `NEBIUS_INCIDENT_EXPLAINER_URL` and `NEBIUS_SCENARIO_GENERATOR_URL` as explicit overrides. When endpoint URLs are not configured, the backend returns typed mock responses.

WebSocket browser smoke test:

```js
const ws = new WebSocket("ws://localhost:8000/ws/arena");
ws.onmessage = (event) => console.log(JSON.parse(event.data));
ws.onopen = () => ws.send(JSON.stringify({ type: "arena_control", action: "start" }));
```

Frontend websocket mode:

```bash
VITE_ARENA_MODE=websocket
VITE_ARENA_WS_URL=ws://localhost:8000/ws/arena
```

Tests:

```bash
uv run pytest
```

## Google Authentication

Configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `AIMADA_JWT_SECRET` for real Google login. `POST /api/auth/google/complete` accepts either `id_token` or `authorization_code`; the Google Identity Services popup code flow sends the browser origin as `redirect_uri`, and redirect-mode clients may send their callback URI explicitly. Once verified, the backend stores the user in `ARENA_OUTPUT_DIR/auth/auth.db` and returns an app-issued JWT.
