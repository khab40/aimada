from enum import StrEnum


class ScenarioType(StrEnum):
    SPOOFING_LIKE_WALL = "spoofing_like_wall"
    LAYERING_LIKE = "layering_like"
    QUOTE_STUFFING = "quote_stuffing"
    LIQUIDITY_EVAPORATION = "liquidity_evaporation"


IMPLEMENTED_SCENARIO_TYPES = tuple(item.value for item in ScenarioType)
BENCHMARK_SCENARIOS = ("normal_market", *IMPLEMENTED_SCENARIO_TYPES)

SCENARIO_LABELS: dict[ScenarioType, str] = {
    ScenarioType.SPOOFING_LIKE_WALL: "Spoofing-like Wall",
    ScenarioType.LAYERING_LIKE: "Layering-like Pattern",
    ScenarioType.QUOTE_STUFFING: "Quote Stuffing Burst",
    ScenarioType.LIQUIDITY_EVAPORATION: "Liquidity Evaporation",
}

SCENARIO_LAUNCH_ENDPOINTS: dict[ScenarioType, str] = {
    ScenarioType.SPOOFING_LIKE_WALL: "/api/scenarios/spoofing-like",
    ScenarioType.LAYERING_LIKE: "/api/scenarios/layering-like",
    ScenarioType.QUOTE_STUFFING: "/api/scenarios/quote-stuffing",
    ScenarioType.LIQUIDITY_EVAPORATION: "/api/scenarios/liquidity-evaporation",
}


def parse_scenario_type(value: str | ScenarioType) -> ScenarioType:
    try:
        return value if isinstance(value, ScenarioType) else ScenarioType(value.strip().lower())
    except ValueError as exc:
        raise ValueError(f"unknown scenario: {value}") from exc
