from typing import Any
from pathlib import Path
from types import SimpleNamespace

from app.api import routes_red_team
from app.nebius.client import RedTeamScenarioResponse
from app.schemas.arena import (
    MarketRegime,
    RedTeamGoal,
    RedTeamScenarioGenerateRequest,
    ScenarioType,
)
from app.storage.local_store import LocalStore


def test_generate_red_team_scenario_returns_launchable_config(monkeypatch: Any, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class FakeNebiusClient:
        def generate_red_team_scenario(
            self,
            prompt: str,
            constraints: dict[str, Any],
        ) -> RedTeamScenarioResponse:
            captured["prompt"] = prompt
            captured["constraints"] = constraints
            return RedTeamScenarioResponse(
                mode="nebius",
                endpoint="Nebius Serverless AI Endpoint",
                scenario_type="quote_stuffing",
                title="Generated quote stuffing burst",
                description="A bounded quote-stuffing burst for the synthetic arena.",
                parameters={"duration_seconds": 4, "message_rate_multiplier": 12},
                expected_detector_risk=0.83,
                safety_note="Educational simulator use only.",
            )

    monkeypatch.setattr(routes_red_team, "nebius_client", FakeNebiusClient())

    config = routes_red_team.generate_red_team_scenario(
        RedTeamScenarioGenerateRequest(
            scenario_family="quote_stuffing",
            market_regime=MarketRegime.VOLATILE,
            goal=RedTeamGoal.HARD_TO_DETECT,
            constraints={"max_duration_seconds": 5},
        ),
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=LocalStore(tmp_path)))),
    )

    assert captured["constraints"]["scenario_family"] == "quote_stuffing"
    assert captured["constraints"]["market_regime"] == "volatile"
    assert captured["constraints"]["goal"] == "hard_to_detect"
    assert "quote_stuffing" in captured["prompt"]
    assert config.slug == ScenarioType.QUOTE_STUFFING
    assert config.launch_endpoint == "/api/scenarios/quote-stuffing"
    assert config.source == "nebius"
    assert config.parameters["duration_seconds"] == 4


def test_red_team_scenario_config_uses_exact_existing_launcher() -> None:
    config = routes_red_team.scenario_config_from_draft(
        RedTeamScenarioResponse(
            mode="mock",
            endpoint="mock Nebius scenario generator",
            scenario_type="liquidity_evaporation",
            title="Liquidity Evaporation",
            description="Draft uses the implemented liquidity scenario.",
            parameters={},
            expected_detector_risk=0.61,
            safety_note="Educational simulator use only.",
        ),
        RedTeamScenarioGenerateRequest(
            scenario_family="liquidity_evaporation",
            market_regime=MarketRegime.THIN_LIQUIDITY,
            goal=RedTeamGoal.OBVIOUS,
            constraints={},
        ),
    )

    assert config.slug == ScenarioType.LIQUIDITY_EVAPORATION
    assert config.scenario_family == "liquidity_evaporation"
    assert config.launch_endpoint == "/api/scenarios/liquidity-evaporation"
