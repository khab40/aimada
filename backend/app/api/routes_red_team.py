from fastapi import APIRouter, Request

from app.nebius.client import NebiusClient, RedTeamScenarioResponse
from app.schemas.arena import (
    RedTeamScenarioGenerateRequest,
    ScenarioConfig,
    ScenarioType,
)
from app.storage.history import append_history_artifact, utc_now

router = APIRouter(prefix="/api/red-team", tags=["red-team"])
nebius_client = NebiusClient()

LAUNCH_ENDPOINTS: dict[ScenarioType, str] = {
    ScenarioType.SPOOFING_LIKE_WALL: "/api/scenarios/spoofing-like",
    ScenarioType.LAYERING_LIKE: "/api/scenarios/layering-like",
    ScenarioType.QUOTE_STUFFING: "/api/scenarios/quote-stuffing",
    ScenarioType.LIQUIDITY_EVAPORATION: "/api/scenarios/liquidity-evaporation",
}

SCENARIO_LABELS: dict[ScenarioType, str] = {
    ScenarioType.SPOOFING_LIKE_WALL: "Spoofing-like Wall",
    ScenarioType.LAYERING_LIKE: "Layering-like Pattern",
    ScenarioType.QUOTE_STUFFING: "Quote Stuffing Burst",
    ScenarioType.LIQUIDITY_EVAPORATION: "Liquidity Evaporation",
}


@router.post("/generate-scenario", response_model=ScenarioConfig)
def generate_red_team_scenario(payload: RedTeamScenarioGenerateRequest, request: Request) -> ScenarioConfig:
    constraints = {
        **payload.constraints,
        "scenario_family": payload.scenario_family,
        "market_regime": payload.market_regime.value,
        "goal": payload.goal.value,
    }
    draft = nebius_client.generate_red_team_scenario(
        prompt=_build_generation_prompt(payload),
        constraints=constraints,
    )
    scenario = scenario_config_from_draft(draft, payload)
    created_at = utc_now()
    row = {
        "created_at": created_at,
        "request": payload.model_dump(mode="json"),
        "scenario": scenario.model_dump(mode="json"),
        "draft": draft.model_dump(mode="json"),
    }
    request.app.state.store.append_jsonl("red-team/generated_scenarios.jsonl", row)
    append_history_artifact(
        request.app.state.store,
        kind="attack_scenario",
        payload=row,
        summary=scenario.label,
        created_at=created_at,
        scenario_id=scenario.slug.value,
        source="red_team_generator",
        source_path="red-team/generated_scenarios.jsonl",
    )
    return scenario


def scenario_config_from_draft(
    draft: RedTeamScenarioResponse,
    request: RedTeamScenarioGenerateRequest,
) -> ScenarioConfig:
    slug = _normalize_scenario_slug(draft.scenario_type, request.scenario_family)
    return ScenarioConfig(
        label=SCENARIO_LABELS[slug],
        slug=slug,
        scenario_family=_scenario_family_for_slug(slug),
        agent_id="ABUSER_01",
        description=draft.description,
        launch_endpoint=LAUNCH_ENDPOINTS[slug],
        parameters=draft.parameters,
        market_regime=request.market_regime,
        goal=request.goal,
        source=draft.mode,
        expected_detector_risk=draft.expected_detector_risk,
        safety_note=draft.safety_note,
    )


def _build_generation_prompt(request: RedTeamScenarioGenerateRequest) -> str:
    return (
        "Generate one bounded educational red-team scenario for the synthetic market abuse detection arena. "
        f"Scenario family: {request.scenario_family}. "
        f"Market regime: {request.market_regime.value}. "
        f"Goal: {request.goal.value}. "
        "Keep the scenario small, synthetic, and launchable by the existing frontend scenario controls."
    )


def _normalize_scenario_slug(raw_type: str, fallback_family: str) -> ScenarioType:
    normalized = (raw_type or fallback_family).lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "spoofing": ScenarioType.SPOOFING_LIKE_WALL,
        "spoofing_like": ScenarioType.SPOOFING_LIKE_WALL,
        "spoofing_like_wall": ScenarioType.SPOOFING_LIKE_WALL,
        "layering": ScenarioType.LAYERING_LIKE,
        "layering_like": ScenarioType.LAYERING_LIKE,
        "quote_stuffing": ScenarioType.QUOTE_STUFFING,
        "quote_stuffing_like": ScenarioType.QUOTE_STUFFING,
        "liquidity_evaporation": ScenarioType.LIQUIDITY_EVAPORATION,
        "liquidity_shock": ScenarioType.LIQUIDITY_EVAPORATION,
        "panic_selloff": ScenarioType.LIQUIDITY_EVAPORATION,
    }
    if normalized in mapping:
        return mapping[normalized]
    return mapping.get(fallback_family.lower().replace("-", "_").replace(" ", "_"), ScenarioType.SPOOFING_LIKE_WALL)


def _scenario_family_for_slug(slug: ScenarioType) -> str:
    families = {
        ScenarioType.SPOOFING_LIKE_WALL: "spoofing_like",
        ScenarioType.LAYERING_LIKE: "layering_like",
        ScenarioType.QUOTE_STUFFING: "quote_stuffing",
        ScenarioType.LIQUIDITY_EVAPORATION: "liquidity_evaporation",
    }
    return families[slug]
