import json
import random
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.experiments.models import Experiment


SCENARIOS = ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"]

EXPECTED_DETECTOR_FAMILIES = {
    "normal_market": None,
    "spoofing": "spoofing_like",
    "layering": "layering_like",
    "quote_stuffing": "quote_stuffing",
    "pump_and_cancel": "liquidity_shock",
}


class AttackManifestRow(BaseModel):
    attack_id: str
    experiment_id: str
    scenario: str
    seed: int
    run_index: int
    expected_has_attack: bool
    expected_detector_family: str | None
    start_tick: int
    duration_ticks: int
    agent_profile: str
    parameters: dict[str, Any]


class AttackManifestResponse(BaseModel):
    experiment_id: str
    path: str
    attack_count: int
    scenarios: list[str]
    status: str


def generate_attack_manifest(experiment: Experiment, artifact_dir: Path) -> list[AttackManifestRow]:
    rng = random.Random(experiment.seed)
    scenarios = _validated_scenarios(experiment.scenarios)
    planned_scenarios = _planned_scenarios(experiment.attack_count, scenarios, rng)
    rows: list[AttackManifestRow] = []

    for run_index, scenario in enumerate(planned_scenarios):
        row_seed = rng.randrange(1, 2**31)
        row_rng = random.Random(row_seed)
        start_tick = row_rng.randint(20, 240)
        duration_ticks = _duration_ticks(scenario, row_rng)
        rows.append(
            AttackManifestRow(
                attack_id=f"{experiment.id}-ATTACK-{run_index + 1:04d}",
                experiment_id=experiment.id,
                scenario=scenario,
                seed=row_seed,
                run_index=run_index,
                expected_has_attack=scenario != "normal_market",
                expected_detector_family=EXPECTED_DETECTOR_FAMILIES[scenario],
                start_tick=start_tick,
                duration_ticks=duration_ticks,
                agent_profile=_agent_profile(scenario, row_rng),
                parameters=_parameters(scenario, row_rng, start_tick, duration_ticks),
            )
        )

    _write_jsonl(artifact_dir / "attacks.jsonl", rows)
    return rows


def _validated_scenarios(values: list[str]) -> list[str]:
    scenarios: list[str] = []
    for value in values:
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in SCENARIOS:
            scenarios.append(normalized)
    if not scenarios:
        return list(SCENARIOS)
    return scenarios


def _planned_scenarios(attack_count: int, scenarios: list[str], rng: random.Random) -> list[str]:
    planned = [scenarios[index % len(scenarios)] for index in range(attack_count)]
    rng.shuffle(planned)
    return planned


def _duration_ticks(scenario: str, rng: random.Random) -> int:
    ranges = {
        "normal_market": (80, 180),
        "spoofing": (24, 72),
        "layering": (40, 120),
        "quote_stuffing": (8, 28),
        "pump_and_cancel": (16, 48),
    }
    low, high = ranges[scenario]
    return rng.randint(low, high)


def _agent_profile(scenario: str, rng: random.Random) -> str:
    profiles = {
        "normal_market": ["balanced_noise", "passive_liquidity", "small_taker"],
        "spoofing": ["large_wall_fast_cancel", "wide_wall_layered_cancel"],
        "layering": ["multi_level_ladder", "staggered_depth_ladder"],
        "quote_stuffing": ["message_burst_cancel", "microburst_quote_churn"],
        "pump_and_cancel": ["aggressive_sweep_cancel", "liquidity_pullback_probe"],
    }
    choices = profiles[scenario]
    return choices[rng.randrange(len(choices))]


def _parameters(scenario: str, rng: random.Random, start_tick: int, duration_ticks: int) -> dict[str, Any]:
    base = {
        "start_tick": start_tick,
        "duration_ticks": duration_ticks,
    }
    if scenario == "normal_market":
        return {
            **base,
            "message_rate_per_tick": round(rng.uniform(0.5, 2.5), 3),
            "max_order_size": rng.randint(2, 12),
        }
    if scenario == "spoofing":
        return {
            **base,
            "wall_size_multiplier": rng.randint(6, 14),
            "distance_from_mid_bps": rng.randint(8, 35),
            "cancel_style": rng.choice(["instant", "gradual", "partial"]),
        }
    if scenario == "layering":
        return {
            **base,
            "levels": rng.randint(3, 8),
            "size_multiplier": rng.randint(3, 9),
            "ladder_spacing_bps": rng.randint(4, 18),
        }
    if scenario == "quote_stuffing":
        return {
            **base,
            "messages_per_tick": rng.randint(18, 60),
            "cancel_ratio": round(rng.uniform(0.72, 0.96), 3),
            "burst_window_ticks": rng.randint(4, 12),
        }
    return {
        **base,
        "sweep_size_multiplier": rng.randint(4, 11),
        "cancel_ratio": round(rng.uniform(0.65, 0.93), 3),
        "pullback_ticks": rng.randint(3, 14),
    }


def _write_jsonl(path: Path, rows: list[AttackManifestRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.model_dump(mode="json"), sort_keys=True) + "\n")
