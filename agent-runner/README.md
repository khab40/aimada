# Agent Runner

Separate process/container for normal-agent decisions.

The Java arena remains the authoritative exchange. This Python runner is retained for AI/ML, heavy, and LangGraph-capable decision work: it receives read-only market snapshots on `POST /decide` and returns `AgentIntent` objects. Java validates, sorts, and applies those intents as a single writer.

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
- `GET /metrics`
- `POST /decide`

LangGraph agents are implemented in `langgraph_agents.py` with `StateGraph`. They use the same `/decide` request and `AgentIntent` response contract as other remote agents.

Metrics are dependency-free Prometheus text metrics for local Grafana dashboards:

- `agent_runner_decide_requests_total`
- `agent_runner_decide_duration_seconds`
- `agent_runner_intents_returned`
- `agent_runner_agents`
- `agent_runner_up`
