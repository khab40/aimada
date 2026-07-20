import asyncio
import importlib.util
import json
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app as backend_app
from app.arena.java_client import JavaArenaClient
from app.metrics import PrometheusTextRegistry


class Response(BytesIO):
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _state() -> dict[str, object]:
    return {
        "tick": 3,
        "running": True,
        "events": [],
        "exchange_events": [],
        "book": {
            "bids": [{"price": 99.0, "quantity": 1.0}],
            "asks": [{"price": 101.0, "quantity": 1.0}],
            "best_bid": 99.0,
            "best_ask": 101.0,
            "mid": 100.0,
            "spread": 2.0,
        },
        "best_bid": 99.0,
        "best_ask": 101.0,
        "mid": 100.0,
        "spread": 2.0,
        "active_agents": [],
        "active_scenario": None,
        "detectors": {"scores": [], "alerts": []},
        "incidents": [],
        "features": {},
    }


def test_prometheus_text_registry_renders_counter_gauge_and_histogram() -> None:
    registry = PrometheusTextRegistry()
    registry.counter("demo_requests_total", "Demo requests.", ("outcome",))
    registry.gauge("demo_up", "Demo up.")
    registry.histogram("demo_duration_seconds", "Demo duration.", ("outcome",), buckets=(0.1, 1.0))

    registry.inc("demo_requests_total", outcome="ok")
    registry.set("demo_up", 1)
    registry.observe("demo_duration_seconds", 0.2, outcome="ok")
    registry.observe("demo_duration_seconds", 2.0, outcome="ok")

    rendered = registry.render()

    assert "# TYPE demo_requests_total counter" in rendered
    assert 'demo_requests_total{outcome="ok"} 1' in rendered
    assert "demo_up 1" in rendered
    assert 'demo_duration_seconds_bucket{outcome="ok",le="0.1"} 0' in rendered
    assert 'demo_duration_seconds_bucket{outcome="ok",le="1"} 1' in rendered
    assert 'demo_duration_seconds_bucket{outcome="ok",le="+Inf"} 2' in rendered
    assert 'demo_duration_seconds_count{outcome="ok"} 2' in rendered
    assert 'demo_duration_seconds_sum{outcome="ok"} 2.2' in rendered


def test_java_arena_client_records_proxy_metrics(monkeypatch) -> None:
    registry = PrometheusTextRegistry()
    registry.counter("backend_java_arena_requests_total", "Requests.", ("method", "endpoint", "outcome"))
    registry.histogram("backend_java_arena_request_duration_seconds", "Duration.", ("method", "endpoint", "outcome"))

    def urlopen(req, timeout: float):
        return Response(json.dumps(_state()).encode())

    monkeypatch.setattr("app.arena.java_client.request.urlopen", urlopen)

    state = asyncio.run(JavaArenaClient("http://java:8080", metrics=registry).get_state())

    assert state.tick == 3
    rendered = registry.render()
    assert 'backend_java_arena_requests_total{method="GET",endpoint="/api/arena/state",outcome="completed"} 1' in rendered
    assert 'backend_java_arena_request_duration_seconds_count{method="GET",endpoint="/api/arena/state",outcome="completed"} 1' in rendered


def test_agent_runner_metrics_endpoint_and_decide_contract(monkeypatch) -> None:
    module_path = Path(__file__).resolve().parents[2] / "agent-runner" / "app.py"
    spec = importlib.util.spec_from_file_location("agent_runner_app_for_metrics_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    monkeypatch.syspath_prepend(str(module_path.parent))
    spec.loader.exec_module(module)

    client = TestClient(module.app)
    metrics_before = client.get("/metrics")

    assert metrics_before.status_code == 200
    assert "agent_runner_up" in metrics_before.text
    assert "agent_runner_agents" in metrics_before.text

    response = client.post(
        "/decide",
        json={
            "snapshot": {
                "tick": 1,
                "bids": [],
                "asks": [],
                "best_bid": 99.0,
                "best_ask": 101.0,
                "mid": 100.0,
                "spread": 2.0,
            }
        },
    )

    assert response.status_code == 200
    metrics_after = client.get("/metrics").text
    assert 'agent_runner_decide_requests_total{runner_id="remote",outcome="completed"} 1' in metrics_after
    assert 'agent_runner_decide_duration_seconds_count{runner_id="remote",outcome="completed"} 1' in metrics_after


def test_backend_metrics_uses_single_state_request_for_incident_count(monkeypatch) -> None:
    class Simulation:
        def __init__(self) -> None:
            self.state_calls = 0
            self.incident_calls = 0

        async def get_state(self) -> SimpleNamespace:
            self.state_calls += 1
            return SimpleNamespace(tick=9, running=True, incidents=[object(), object()])

        async def list_incidents(self) -> list[object]:
            self.incident_calls += 1
            raise AssertionError("backend /metrics should use incidents from ArenaState")

    simulation = Simulation()
    monkeypatch.setattr(backend_app.state, "simulation", simulation)

    response = TestClient(backend_app).get("/metrics")

    assert response.status_code == 200
    assert "arena_tick 9" in response.text
    assert "arena_incidents_total 2" in response.text
    assert simulation.state_calls == 1
    assert simulation.incident_calls == 0
