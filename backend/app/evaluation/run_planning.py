import json
import random
from collections.abc import Mapping, Sequence


DIFFICULTIES = ("easy", "medium", "hard", "adversarial")
DEFAULT_DIFFICULTY_MIX = {"easy": 0.2, "medium": 0.5, "hard": 0.2, "adversarial": 0.1}


def parse_difficulty_mix(value: str | Mapping[str, float]) -> dict[str, float]:
    decoded = json.loads(value) if isinstance(value, str) else dict(value)
    unknown = set(decoded) - set(DIFFICULTIES)
    if unknown:
        raise ValueError(f"unknown difficulties: {', '.join(sorted(unknown))}")
    weights = {name: float(decoded.get(name, 0.0)) for name in DIFFICULTIES}
    if any(weight < 0 for weight in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError("difficulty weights must be non-negative and sum to more than zero")
    total = sum(weights.values())
    return {name: weight / total for name, weight in weights.items()}


def exact_balanced_plan(total: int, values: Sequence[str], *, seed: int) -> list[str]:
    if total < 1:
        raise ValueError("total must be positive")
    if not values:
        raise ValueError("at least one value is required")
    plan = [values[index % len(values)] for index in range(total)]
    random.Random(seed).shuffle(plan)
    return plan


def exact_weighted_plan(total: int, weights: Mapping[str, float], *, seed: int) -> list[str]:
    normalized = parse_difficulty_mix(weights)
    raw = {name: normalized[name] * total for name in DIFFICULTIES}
    counts = {name: int(raw[name]) for name in DIFFICULTIES}
    remaining = total - sum(counts.values())
    ranked = sorted(DIFFICULTIES, key=lambda name: (raw[name] - counts[name], -DIFFICULTIES.index(name)), reverse=True)
    for name in ranked[:remaining]:
        counts[name] += 1
    plan = [name for name in DIFFICULTIES for _ in range(counts[name])]
    random.Random(seed).shuffle(plan)
    return plan


def engine_profile(difficulty: str) -> dict[str, float | int]:
    profiles: dict[str, dict[str, float | int]] = {
        "easy": {"baseline_liquidity_base_size": 1.0, "normal_agent_count": 2},
        "medium": {"baseline_liquidity_base_size": 1.5, "normal_agent_count": 3},
        "hard": {"baseline_liquidity_base_size": 2.5, "normal_agent_count": 4},
        "adversarial": {"baseline_liquidity_base_size": 4.0, "normal_agent_count": 5},
    }
    if difficulty not in profiles:
        raise ValueError(f"unknown difficulty: {difficulty}")
    return profiles[difficulty]
