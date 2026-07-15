import hashlib
import json
import random
from collections.abc import Mapping, Sequence


DIFFICULTIES = ("easy", "medium", "hard", "adversarial")
DEFAULT_DIFFICULTY_MIX = {"easy": 0.2, "medium": 0.5, "hard": 0.2, "adversarial": 0.1}


def derive_run_seed(base_seed: int, run_index: int) -> int:
    """Derive independent, reproducible run seeds without overlapping adjacent experiments."""
    if base_seed < 0 or run_index < 0:
        raise ValueError("base seed and run index must be non-negative")
    digest = hashlib.sha256(f"lob-arena:{base_seed}:{run_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % 2_147_483_647


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


def engine_profile(difficulty: str, *, seed: int | None = None) -> dict[str, float | int]:
    profiles: dict[str, dict[str, float | int]] = {
        "easy": {"baseline_liquidity_base_size": 1.0, "normal_agent_count": 2},
        "medium": {"baseline_liquidity_base_size": 1.5, "normal_agent_count": 3},
        "hard": {"baseline_liquidity_base_size": 2.5, "normal_agent_count": 4},
        "adversarial": {"baseline_liquidity_base_size": 4.0, "normal_agent_count": 5},
    }
    if difficulty not in profiles:
        raise ValueError(f"unknown difficulty: {difficulty}")
    profile = dict(profiles[difficulty])
    if seed is None:
        return profile

    rng = random.Random(seed)
    profile["baseline_liquidity_reference_price"] = round(68_125.0 * rng.uniform(0.985, 1.015), 2)
    profile["baseline_liquidity_tick_size"] = rng.choice((0.5, 1.0, 2.0))
    profile["baseline_liquidity_base_size"] = round(
        float(profile["baseline_liquidity_base_size"]) * rng.uniform(0.8, 1.2),
        3,
    )
    profile["normal_agent_count"] = max(
        1,
        int(profile["normal_agent_count"]) + rng.choice((-1, 0, 1)),
    )
    return profile
