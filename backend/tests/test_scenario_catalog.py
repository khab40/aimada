from pathlib import Path

import pytest

from app.api.routes_nebius import AttackScenarioInput
from app.arena.engine import SimulationEngine
from app.scenarios.catalog import IMPLEMENTED_SCENARIO_TYPES, ScenarioType, parse_scenario_type


EXPECTED_SCENARIOS = (
    "spoofing_like_wall",
    "layering_like",
    "quote_stuffing",
    "liquidity_evaporation",
)


def test_catalog_contains_only_native_arena_scenarios() -> None:
    assert IMPLEMENTED_SCENARIO_TYPES == EXPECTED_SCENARIOS
    for scenario in EXPECTED_SCENARIOS:
        assert parse_scenario_type(scenario) == ScenarioType(scenario)


def test_unsupported_scenario_is_not_aliased() -> None:
    unsupported = "pump" + "_and_cancel"
    try:
        parse_scenario_type(unsupported)
    except ValueError as exc:
        assert "unknown scenario" in str(exc)
    else:
        raise AssertionError("unsupported scenario must be rejected")


def test_attack_generator_rejects_unsupported_scenario_label() -> None:
    unsupported = "Pump" + " and Cancel"
    with pytest.raises(ValueError, match="unknown attack scenario"):
        AttackScenarioInput(attackType=unsupported)


def test_quote_stuffing_is_an_executable_place_cancel_burst() -> None:
    engine = SimulationEngine(normal_agent_count=0)
    engine.launch_scenario(ScenarioType.QUOTE_STUFFING.value)

    state = {}
    for _ in range(5):
        state = engine.step()

    burst_events = [event for event in state["events"] if event.get("scenario_family") == "quote_stuffing"]
    assert len([event for event in burst_events if event.get("message") == "rapid place/cancel quote update"]) >= 8
    assert state["features"]["message_rate"] > 0


def test_frontend_catalog_matches_backend_catalog() -> None:
    frontend_catalog = (Path(__file__).resolve().parents[2] / "frontend/src/scenarios.ts").read_text(encoding="utf-8")
    for scenario in EXPECTED_SCENARIOS:
        assert f'"{scenario}"' in frontend_catalog


def test_active_repository_has_no_phantom_scenario_names() -> None:
    root = Path(__file__).resolve().parents[2]
    excluded_dirs = {".git", ".venv", "archived", "dist", "evidence", "node_modules", "outputs"}
    text_suffixes = {".example", ".js", ".json", ".md", ".mjs", ".py", ".sh", ".ts", ".tsx", ".yaml", ".yml"}
    forbidden = (
        "pump" + "_and_cancel",
        "panic" + "_selloff",
        "momentum" + "_ignition",
        "wash" + "_trading",
        "quote_stuffing" + "_like",
    )
    violations: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file() or excluded_dirs.intersection(path.parts):
            continue
        if path.suffix not in text_suffixes and path.name not in {"Dockerfile", "Makefile"}:
            continue
        normalized = path.read_text(encoding="utf-8", errors="ignore").lower().replace("-", "_").replace(" ", "_")
        if any(name in normalized for name in forbidden):
            violations.append(str(path.relative_to(root)))

    assert violations == []
