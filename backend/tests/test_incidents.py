import asyncio
import json
from typing import Any

from app.api.routes_incidents import build_compact_replay_payload
from app.arena.engine import SimulationEngine
from app.config import get_settings
from app.nebius.client import NebiusClient


def test_incident_is_created_when_detector_crosses_threshold() -> None:
    engine = SimulationEngine()

    engine.launch_scenario("quote-stuffing")
    for _ in range(5):
        state = engine.step()

    assert state["incidents"]
    incident = state["incidents"][0]
    assert incident["id"] == "INC-000001"
    assert incident["type"] == "quote_stuffing"
    assert incident["confidence"] >= 0.80
    assert len(incident["evidence"]) >= 2


def test_incident_creation_is_deduplicated_per_scenario_detector() -> None:
    engine = SimulationEngine()

    engine.launch_scenario("quote-stuffing")
    for _ in range(8):
        state = engine.step()

    quote_incidents = [
        incident for incident in state["incidents"]
        if incident["type"] == "quote_stuffing"
    ]
    assert len(quote_incidents) == 1


def test_incident_lookup_and_mock_explanation() -> None:
    async def run() -> None:
        engine = SimulationEngine()
        engine.launch_scenario("quote-stuffing")
        for _ in range(5):
            engine.step()

        incidents = await engine.list_incidents()
        incident = await engine.get_incident("INC-000001")

        assert incidents
        assert incident is not None
        explanation = NebiusClient(incident_explainer_url="").explain_incident(incident)
        assert explanation is not None
        assert explanation.mode == "mock"
        assert explanation.endpoint == "mock Nebius AI explanation"
        assert explanation.fallback_reason == "NEBIUS_INCIDENT_EXPLAINER_URL is not configured"
        assert explanation.incident_id == "INC-000001"

    asyncio.run(run())


def test_nebius_client_posts_structured_incident_evidence(monkeypatch: Any) -> None:
    async def run() -> None:
        engine = SimulationEngine()
        engine.launch_scenario("quote-stuffing")
        for _ in range(5):
            engine.step()

        incident = await engine.get_incident("INC-000001")
        assert incident is not None

        captured: dict[str, Any] = {}

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "risk_level": "high",
                        "plain_english_summary": "Synthetic quote-stuffing evidence explained.",
                    }
                ).encode("utf-8")

        def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["timeout"] = timeout
            captured["authorization"] = request.get_header("Authorization")
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        monkeypatch.setattr("app.nebius.client.urlopen", fake_urlopen)

        state = await engine.get_state()
        replay_payload = build_compact_replay_payload(incident, state)
        explanation = NebiusClient(
            incident_explainer_url="http://example.test/explain-event",
            api_key="test-token",
            timeout_seconds=1.5,
        ).explain_incident(incident, replay_payload=replay_payload)

        assert captured["url"] == "http://example.test/explain-event"
        assert captured["method"] == "POST"
        assert captured["timeout"] == 1.5
        assert captured["authorization"] == "Bearer test-token"
        assert captured["payload"]["incident_id"] == "INC-000001"
        assert captured["payload"]["type"] == "quote_stuffing"
        assert captured["payload"]["evidence"]
        assert captured["payload"]["replay"]["window"]["incident_id"] == "INC-000001"
        assert len(captured["payload"]["replay"]["book"]["bids"]) <= 5
        assert len(captured["payload"]["replay"]["recent_events"]) <= 10
        assert {"key", "label", "value", "unit", "interpretation"} <= set(
            captured["payload"]["evidence"][0]
        )
        assert explanation.mode == "nebius"
        assert explanation.risk_level == "high"

    asyncio.run(run())


def test_compact_replay_payload_contains_bounded_market_context() -> None:
    async def run() -> None:
        engine = SimulationEngine()
        engine.launch_scenario("quote-stuffing")
        for _ in range(5):
            engine.step()

        incident = await engine.get_incident("INC-000001")
        state = await engine.get_state()
        assert incident is not None

        payload = build_compact_replay_payload(incident, state)

        assert payload["window"]["basis"] == "latest_in_memory_state"
        assert payload["window"]["incident_id"] == "INC-000001"
        assert payload["market"]["mid"] == state.mid
        assert len(payload["book"]["bids"]) <= 5
        assert len(payload["book"]["asks"]) <= 5
        assert len(payload["recent_events"]) <= 10
        assert payload["detectors"]
        assert "events" not in payload

    asyncio.run(run())


def test_nebius_client_generates_mock_red_team_scenario_without_endpoint() -> None:
    scenario = NebiusClient(scenario_generator_url="").generate_red_team_scenario(
        prompt="short spoofing-like wall",
        constraints={"scenario_type": "spoofing_like_wall", "lifetime_seconds": 4},
    )

    assert scenario.mode == "mock"
    assert scenario.scenario_type == "spoofing_like_wall"
    assert scenario.parameters["lifetime_seconds"] == 4
    assert scenario.fallback_reason == "NEBIUS_SCENARIO_GENERATOR_URL is not configured"


def test_nebius_client_status_reports_cli_shape() -> None:
    status = NebiusClient().integration_status()

    assert isinstance(status.cli_installed, bool)
    assert isinstance(status.tenant_id_configured, bool)
    assert isinstance(status.incident_explainer_configured, bool)


def test_nebius_endpoint_base_url_derives_backend_routes(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_BASE_URL", "https://nebius-endpoint.example")
    monkeypatch.setenv("NEBIUS_INCIDENT_EXPLAINER_URL", "")
    monkeypatch.setenv("NEBIUS_SCENARIO_GENERATOR_URL", "")
    get_settings.cache_clear()

    try:
        client = NebiusClient()
        status = client.integration_status()

        assert client.incident_explainer_url == "https://nebius-endpoint.example/explain-event"
        assert client.scenario_generator_url == "https://nebius-endpoint.example/generate-scenario"
        assert status.incident_explainer_configured is True
        assert status.scenario_generator_configured is True
    finally:
        get_settings.cache_clear()
