import json
from pathlib import Path

import pytest

from app.contracts.determinism import (
    EventOrderKey,
    SplitMix64,
    decimal_to_units,
    derive_stream_seed,
    midpoint_ticks_x2,
    quantize_metric,
    simulation_event_id,
)

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "contracts" / "golden" / "determinism-v1.json"


def golden() -> dict[str, object]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_splitmix64_matches_language_neutral_vectors() -> None:
    for vector in golden()["splitmix64"]:
        random = SplitMix64(vector["seed"])
        assert [f"{random.next_u64():016x}" for _ in vector["outputs_hex"]] == vector["outputs_hex"]


def test_named_stream_seeds_match_sha256_vectors() -> None:
    for vector in golden()["stream_seeds"]:
        derived = derive_stream_seed(vector["root_seed"], vector["stream_name"])
        assert f"{derived:016x}" == vector["derived_seed_hex"]


def test_event_order_is_total_and_matches_fixture() -> None:
    fixture = golden()["event_order"]
    ordered = sorted(
        fixture["unordered"],
        key=lambda item: EventOrderKey(
            logical_time=item["logical_time"],
            phase=item["phase"],
            source_priority=item["source_priority"],
            actor_id=item["actor_id"],
            source_sequence=item["source_sequence"],
            insertion_sequence=item["insertion_sequence"],
        ),
    )

    assert [item["id"] for item in ordered] == fixture["expected_ids"]


def test_numeric_units_metrics_midpoints_and_event_ids_match_vectors() -> None:
    fixture = golden()
    for vector in fixture["numeric"]:
        assert decimal_to_units(vector["value"], unit_size_nanos=vector["unit_size_nanos"]) == vector["expected_units"]
    for vector in fixture["metrics"]:
        assert quantize_metric(vector["value"], decimal_scale=vector["decimal_scale"]) == vector["expected_quantized"]
    for vector in fixture["midpoints"]:
        assert midpoint_ticks_x2(vector["best_bid_ticks"], vector["best_ask_ticks"]) == vector["expected_mid_ticks_x2"]
    for vector in fixture["event_ids"]:
        assert simulation_event_id(vector["venue"], vector["event_type"], vector["sequence"]) == vector["expected"]


def test_contract_rejects_non_integral_units_and_ambiguous_identifiers() -> None:
    with pytest.raises(ValueError, match="not an exact multiple"):
        decimal_to_units("1.0000005", unit_size_nanos=1_000)
    with pytest.raises(ValueError, match="without ':'"):
        simulation_event_id("SIM:BAD", "add", 1)
    with pytest.raises(ValueError, match="ASCII"):
        EventOrderKey(1, 10, 0, "агент", 0, 0)
