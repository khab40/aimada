import asyncio
import json
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError

from app.api.routes_incidents import build_compact_replay_payload, persist_explanation_result
from app.arena.engine import SimulationEngine
from app.config import get_settings
from app.nebius.client import AIInvestigationTeamRequest, InvestigationReportRequest, NebiusClient, OrderBookAlertRequest
from app.nebius.adapters import MockNebiusCloudAdapter
from app.nebius.scenario_generator import MarketAbuseScenarioGenerationRequest, project_attack_scenario
from app.storage.local_store import LocalStore


def test_runtime_health_uses_live_probe_results_without_ready_defaults() -> None:
    health = MockNebiusCloudAdapter().runtime_health(
        cli_installed=True,
        endpoint_health={"status": "unreachable", "fallback_reason": "probe failed"},
        job_health={"status": "ok", "detail": "live probe succeeded"},
        storage_health={"status": "not_configured", "detail": "missing output URI"},
    )
    by_name = {item["name"]: item for item in health}

    assert by_name["Nebius CLI"]["status"] == "installed"
    assert by_name["Nebius AI Endpoint"]["status"] == "unreachable"
    assert by_name["Nebius Serverless Jobs"]["status"] == "ok"
    assert by_name["Nebius Object Storage"]["status"] == "not_configured"
    assert all(item["status"] != "ready" for item in health)


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
        assert all(item.key in payload["features"] for item in incident.evidence)
        assert "events" not in payload

    asyncio.run(run())


def test_incident_explanation_result_is_persisted(tmp_path: Any) -> None:
    async def run() -> None:
        engine = SimulationEngine(store=LocalStore(tmp_path))
        engine.launch_scenario("quote-stuffing")
        for _ in range(5):
            engine.step()

        incident = await engine.get_incident("INC-000001")
        state = await engine.get_state()
        assert incident is not None

        explanation = NebiusClient(incident_explainer_url="").explain_incident(incident)
        replay_payload = build_compact_replay_payload(incident, state)
        stored = persist_explanation_result(
            store=engine.store,
            incident=incident,
            explanation=explanation,
            replay_payload=replay_payload,
        )
        rows = engine.store.read_jsonl("incidents/explanations.jsonl")
        significant_events = engine.store.read_jsonl("events/significant_events.jsonl")

        assert stored.explanation_id is not None
        assert stored.created_at is not None
        assert stored.stored_artifact == "incidents/explanations.jsonl"
        assert rows
        assert rows[-1]["id"] == stored.explanation_id
        assert rows[-1]["incident_id"] == "INC-000001"
        assert rows[-1]["explanation"]["plain_english_summary"]
        assert significant_events[-1]["type"] == "nebius_incident_explanation"

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


def test_nebius_client_generates_mock_market_abuse_scenario_without_endpoint() -> None:
    scenario = NebiusClient(market_abuse_scenario_url="").generate_market_abuse_scenario(
        MarketAbuseScenarioGenerationRequest(
            manipulation_type="layering",
            difficulty="hard",
            symbol="NBS",
            duration_ticks=180,
            liquidity_regime="thin",
            volatility_regime="high",
            seed=7,
        )
    )
    projection = project_attack_scenario(scenario)

    assert scenario.mode == "mock"
    assert scenario.manipulation_type == "layering"
    assert scenario.ground_truth.label == "layering"
    assert scenario.events
    assert scenario.replay["route"] == "layering-like"
    assert projection["id"] == scenario.scenario_id
    assert projection["attackType"] == "layering"
    assert projection["source"]["ground_truth"]["label"] == "layering"


def test_nebius_client_uses_compatible_scenario_route_when_specialized_route_is_missing(monkeypatch: Any) -> None:
    client = NebiusClient(
        market_abuse_scenario_url="https://endpoint.example/generate-market-abuse-scenario",
        scenario_generator_url="https://endpoint.example/generate-scenario",
    )
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((url, payload))
        if url.endswith("/generate-market-abuse-scenario"):
            raise HTTPError(url, 404, "Not Found", None, None)
        return {
            "description": "Endpoint-generated bounded scenario explanation.",
            "model": "deployed-model",
            "model_mode": "vllm",
            "title": "Compatible endpoint scenario",
        }

    monkeypatch.setattr(client, "_post_json", fake_post)
    scenario = client.generate_market_abuse_scenario(MarketAbuseScenarioGenerationRequest(seed=13))

    assert [url for url, _ in calls] == [
        "https://endpoint.example/generate-market-abuse-scenario",
        "https://endpoint.example/generate-scenario",
    ]
    assert scenario.mode == "nebius"
    assert scenario.endpoint.endswith("/generate-scenario")
    assert scenario.title == "Compatible endpoint scenario"
    assert scenario.events
    assert scenario.fallback_reason is None


def test_nebius_client_uses_deployed_orderbook_route_when_scenario_routes_are_missing(monkeypatch: Any) -> None:
    client = NebiusClient(
        market_abuse_scenario_url="https://endpoint.example/generate-market-abuse-scenario",
        orderbook_alert_url="https://endpoint.example/orderbook-alert",
        scenario_generator_url="https://endpoint.example/generate-scenario",
    )
    calls: list[str] = []

    def fake_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(url)
        if not url.endswith("/orderbook-alert"):
            raise HTTPError(url, 404, "Not Found", None, None)
        assert payload["scenario_hint"] == "spoofing"
        return {
            "confidence": 0.9,
            "detected_pattern": "Spoofing",
            "model": "deployed-model",
            "model_mode": "local_vllm",
            "reasons": ["Endpoint analyzed the bounded synthetic order-book pattern."],
            "recommended_action": "Review the synthetic replay and detector evidence.",
            "suspicion_score": 0.7,
        }

    monkeypatch.setattr(client, "_post_json", fake_post)
    scenario = client.generate_market_abuse_scenario(MarketAbuseScenarioGenerationRequest(seed=21))

    assert calls[-1].endswith("/orderbook-alert")
    assert scenario.mode == "nebius"
    assert scenario.endpoint.endswith("/orderbook-alert")
    assert scenario.source["compatibility_mode"] == "orderbook_alert_analysis"
    assert scenario.source["model_mode"] == "local_vllm"
    assert scenario.fallback_reason is None


def test_nebius_client_status_reports_cli_shape(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_BASE_URL", "")
    monkeypatch.setenv("NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_STATUS_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_OUTPUT_URI", "")
    get_settings.cache_clear()

    try:
        status = NebiusClient().integration_status()
    finally:
        get_settings.cache_clear()

    assert isinstance(status.cli_installed, bool)
    assert isinstance(status.tenant_id_configured, bool)
    assert isinstance(status.incident_explainer_configured, bool)
    assert isinstance(status.orderbook_alert_configured, bool)
    assert isinstance(status.investigation_report_configured, bool)
    assert isinstance(status.investigation_team_configured, bool)


def test_nebius_endpoint_base_url_derives_backend_routes(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_BASE_URL", "https://nebius-endpoint.example")
    monkeypatch.setenv("NEBIUS_INCIDENT_EXPLAINER_URL", "")
    monkeypatch.setenv("NEBIUS_SCENARIO_GENERATOR_URL", "")
    monkeypatch.setenv("NEBIUS_ORDERBOOK_ALERT_URL", "")
    monkeypatch.setenv("NEBIUS_INVESTIGATION_REPORT_URL", "")
    monkeypatch.setenv("ENDPOINT_TOKEN", "test-token")
    monkeypatch.setenv("NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_STATUS_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_OUTPUT_URI", "")
    get_settings.cache_clear()

    captured: dict[str, Any] = {}

    class FakeHealthResponse:
        def __enter__(self) -> "FakeHealthResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "status": "ok",
                    "endpoint_mode": "local_vllm",
                    "model": "Qwen/Qwen2.5-14B-Instruct",
                }
            ).encode("utf-8")

    def fake_urlopen(request: Any, timeout: float) -> FakeHealthResponse:
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["authorization"] = request.get_header("Authorization")
        return FakeHealthResponse()

    monkeypatch.setattr("app.nebius.client.urlopen", fake_urlopen)

    try:
        client = NebiusClient()
        status = client.integration_status()

        assert client.incident_explainer_url == "https://nebius-endpoint.example/explain-event"
        assert client.scenario_generator_url == "https://nebius-endpoint.example/generate-scenario"
        assert client.market_abuse_scenario_url == "https://nebius-endpoint.example/generate-market-abuse-scenario"
        assert client.orderbook_alert_url == "https://nebius-endpoint.example/orderbook-alert"
        assert client.investigation_report_url == "https://nebius-endpoint.example/investigation-report"
        assert status.incident_explainer_configured is True
        assert status.scenario_generator_configured is True
        assert status.orderbook_alert_configured is True
        assert status.investigation_report_configured is True
        assert status.investigation_team_configured is True
        assert status.endpoint_base_url_configured is True
        assert status.endpoint_mode == "local_vllm"
        assert status.model == "Qwen/Qwen2.5-14B-Instruct"
        assert status.endpoint_health == {
            "status": "ok",
            "endpoint_mode": "local_vllm",
            "model": "Qwen/Qwen2.5-14B-Instruct",
        }
        assert captured["url"] == "https://nebius-endpoint.example/health"
        assert captured["method"] == "GET"
        assert captured["authorization"] == "Bearer test-token"
    finally:
        get_settings.cache_clear()


def test_nebius_job_health_requires_successful_live_probe(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE", "submit-job")
    monkeypatch.setenv("NEBIUS_JOB_STATUS_COMMAND_TEMPLATE", "status-job {job_id}")
    monkeypatch.setenv("NEBIUS_JOB_HEALTH_COMMAND", "nebius ai job list --format json")
    monkeypatch.setattr(
        "app.nebius.client.subprocess.run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1, stdout="private-output", stderr="secret"),
    )
    get_settings.cache_clear()
    try:
        health = NebiusClient().job_health(cli_path="/usr/bin/nebius")
    finally:
        get_settings.cache_clear()

    assert health["status"] == "unreachable"
    assert "private-output" not in health["detail"]
    assert "secret" not in health["detail"]


def test_nebius_job_health_reports_connected_only_after_success(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE", "submit-job")
    monkeypatch.setenv("NEBIUS_JOB_STATUS_COMMAND_TEMPLATE", "status-job {job_id}")
    monkeypatch.setenv("NEBIUS_JOB_HEALTH_COMMAND", "nebius ai job list --format json")
    monkeypatch.setattr(
        "app.nebius.client.subprocess.run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="{}", stderr=""),
    )
    get_settings.cache_clear()
    try:
        health = NebiusClient().job_health(cli_path="/usr/bin/nebius")
    finally:
        get_settings.cache_clear()

    assert health["status"] == "ok"


def test_nebius_endpoint_explicit_urls_override_base_url(monkeypatch: Any) -> None:
    monkeypatch.setenv("NEBIUS_ENDPOINT_BASE_URL", "https://base.example")
    monkeypatch.setenv("NEBIUS_INCIDENT_EXPLAINER_URL", "https://override.example/explain")
    monkeypatch.setenv("NEBIUS_SCENARIO_GENERATOR_URL", "https://override.example/scenario")
    monkeypatch.setenv("NEBIUS_ORDERBOOK_ALERT_URL", "https://override.example/orderbook")
    monkeypatch.setenv("NEBIUS_INVESTIGATION_REPORT_URL", "https://override.example/report")
    get_settings.cache_clear()

    try:
        client = NebiusClient()

        assert client.incident_explainer_url == "https://override.example/explain"
        assert client.scenario_generator_url == "https://override.example/scenario"
        assert client.orderbook_alert_url == "https://override.example/orderbook"
        assert client.investigation_report_url == "https://override.example/report"
    finally:
        get_settings.cache_clear()


def test_nebius_client_posts_orderbook_alert_to_deployed_endpoint(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "suspicion_score": 0.82,
                    "detected_pattern": "spoofing_like_wall",
                    "confidence": 0.8,
                    "reasons": ["synthetic wall"],
                    "recommended_action": "review replay",
                }
            ).encode("utf-8")

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.nebius.client.urlopen", fake_urlopen)

    response = NebiusClient(
        orderbook_alert_url="https://endpoint.example/orderbook-alert",
        api_key="test-token",
        timeout_seconds=1.25,
    ).detect_orderbook_alert(
        OrderBookAlertRequest(
            bids=[{"price": 100.0, "quantity": 20.0}],
            asks=[{"price": 101.0, "quantity": 2.0}],
            features={"wall_size_ratio": 8.5},
            scenario_hint="spoofing",
            tick=42,
        )
    )

    assert captured["url"] == "https://endpoint.example/orderbook-alert"
    assert captured["method"] == "POST"
    assert captured["authorization"] == "Bearer test-token"
    assert captured["payload"]["tick"] == 42
    assert response.mode == "nebius"
    assert response.endpoint == "https://endpoint.example/orderbook-alert"
    assert response.detected_pattern == "spoofing_like_wall"
    assert response.reasons == ["synthetic wall"]


def test_nebius_client_posts_investigation_report_to_deployed_endpoint(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "title": "Endpoint report",
                    "summary": "Endpoint summary",
                    "timeline": ["alert created"],
                    "detector_findings": ["high confidence"],
                    "limitations": ["synthetic only"],
                    "recommended_next_steps": ["review artifacts"],
                }
            ).encode("utf-8")

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.nebius.client.urlopen", fake_urlopen)

    response = NebiusClient(
        investigation_report_url="https://endpoint.example/investigation-report",
        api_key="test-token",
    ).investigation_report(
        InvestigationReportRequest(
            scenario_trace={"scenario": "spoofing"},
            alerts=[{"confidence": 0.92}],
            metrics={"precision": 0.9},
        )
    )

    assert captured["url"] == "https://endpoint.example/investigation-report"
    assert captured["method"] == "POST"
    assert captured["authorization"] == "Bearer test-token"
    assert captured["payload"]["scenario_trace"]["scenario"] == "spoofing"
    assert response.mode == "nebius"
    assert response.endpoint == "https://endpoint.example/investigation-report"
    assert response.title == "Endpoint report"


def test_nebius_client_posts_investigation_team_to_deployed_endpoint(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "investigation_id": "INV-1",
                    "manipulation_type": "spoofing",
                    "risk_score": 0.88,
                    "confidence": 0.91,
                    "agents": [
                        {
                            "name": "OrderBookExpertAgent",
                            "role": "Order book reviewer",
                            "finding": "wall detected",
                            "confidence": 0.9,
                            "evidence": ["wall_size_ratio=8.2"],
                        }
                    ],
                    "consensus": "spoofing likely",
                    "evidence_timeline": ["wall placed", "wall canceled"],
                    "recommended_action": "review replay",
                    "executive_summary": "team summary",
                }
            ).encode("utf-8")

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.nebius.client.urlopen", fake_urlopen)

    response = NebiusClient(
        investigation_team_url="https://endpoint.example/investigation-team",
        api_key="test-token",
    ).analyze_investigation_team(
        AIInvestigationTeamRequest(
            incident={"incident_id": "INC-1", "type": "spoofing", "confidence": 0.9},
            detector_outputs=[{"detector": "wall", "confidence": 0.91}],
            episode_summary={
                "market_regime": {"liquidity": "thin"},
                "event_timeline": [{"sequence": 1, "event": "wall placed"}],
            },
            market_metrics={"wall_size_ratio": 8.2},
        )
    )

    assert captured["url"] == "https://endpoint.example/investigation-team"
    assert captured["method"] == "POST"
    assert captured["authorization"] == "Bearer test-token"
    assert captured["payload"]["incident"]["incident_id"] == "INC-1"
    assert captured["payload"]["episode_summary"]["market_regime"]["liquidity"] == "thin"
    assert response.mode == "nebius"
    assert response.investigation_id == "INV-1"
    assert response.agents[0].name == "OrderBookExpertAgent"


def test_nebius_client_investigation_team_mock_is_deterministic() -> None:
    response = NebiusClient(investigation_team_url="").analyze_investigation_team(
        AIInvestigationTeamRequest(
            incident={"incident_id": "INC-1", "type": "spoofing", "confidence": 0.88, "tick": 12},
            detector_outputs=[{"detected_pattern": "spoofing_like_wall", "confidence": 0.91}],
            order_book_context={"events": [{"type": "quote"}]},
            trades=[{"price": 100.0}],
            market_metrics={"wall_size_ratio": 8.2, "cancel_to_trade_ratio": 5.4},
        )
    )

    assert response.mode == "mock"
    assert response.investigation_id == "INC-1"
    assert response.manipulation_type == "spoofing"
    assert response.risk_score == 0.91
    assert [agent.name for agent in response.agents] == [
        "OrderBookExpertAgent",
        "TradePatternAgent",
        "StatisticsAgent",
        "ComplianceAgent",
        "LeadInvestigatorAgent",
    ]
    assert response.evidence_timeline


def test_nebius_client_falls_back_when_deployed_endpoint_fails(monkeypatch: Any) -> None:
    def fake_urlopen(request: Any, timeout: float) -> None:
        raise URLError("down")

    monkeypatch.setattr("app.nebius.client.urlopen", fake_urlopen)

    response = NebiusClient(
        orderbook_alert_url="https://endpoint.example/orderbook-alert",
        timeout_seconds=0.01,
    ).detect_orderbook_alert(
        OrderBookAlertRequest(features={"wall_size_ratio": 8.5}, scenario_hint="spoofing")
    )

    assert response.mode == "mock"
    assert response.fallback_reason is not None
    assert "Nebius order-book alert fallback" in response.fallback_reason
