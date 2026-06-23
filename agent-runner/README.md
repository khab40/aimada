# Agent Runner

Separate process/container for normal-agent decisions.

The arena backend remains the authoritative exchange. This runner receives read-only market snapshots on `POST /decide` and returns `AgentIntent` objects. The backend sorts and applies those intents as a single writer.

Environment:

```bash
AGENT_RUNNER_AGENT_COUNT=200
AGENT_RUNNER_HEAVY_AGENT_COUNT=8
AGENT_RUNNER_HEAVY_AGENT_COMPLEXITY=20000
AGENT_RUNNER_HEAVY_AGENT_WORKERS=2
AGENT_RUNNER_LANGGRAPH_AGENT_COUNT=16
AGENT_RUNNER_LANGGRAPH_STRATEGY=liquidity_rebalancer
AGENT_RUNNER_AGENT_ID_PREFIX=REMOTE
AGENT_RUNNER_DECISION_TIMEOUT_SECONDS=0.05
```

Endpoints:

- `GET /health`
- `GET /agents`
- `POST /decide`

LangGraph agents are implemented in `langgraph_agents.py` with `StateGraph`. They use the same `/decide` request and `AgentIntent` response contract as other remote agents.
