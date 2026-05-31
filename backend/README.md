# Backend

FastAPI backend for the live arena demo.

## Responsibilities

- Start and stop synthetic simulations.
- Launch abuse-like scenarios.
- Broadcast arena events over WebSocket.
- Store local event, snapshot, incident, and report artifacts.
- Proxy explanation requests to the Nebius AI endpoint.

## Local Development

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
uv run pytest
```
