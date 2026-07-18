import hashlib
import json
from collections import Counter
from pathlib import Path

from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.hashing import book_hash, event_stream_hash


ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = ROOT / "contracts" / "golden" / "parity-v1"


def test_manifest_checksums_and_results_are_self_consistent() -> None:
    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["corpus_version"] == 1
    assert manifest["contract_version"] == 1
    assert len(manifest["cases"]) == 6
    assert len({item["case_id"] for item in manifest["cases"]}) == len(manifest["cases"])
    for item in manifest["cases"]:
        request_bytes = (CORPUS_ROOT / item["request_file"]).read_bytes()
        result_bytes = (CORPUS_ROOT / item["expected_result_file"]).read_bytes()
        request = exchange_pb2.SimulationRequest.FromString(request_bytes)
        result = exchange_pb2.SimulationResult.FromString(result_bytes)

        assert hashlib.sha256(request_bytes).hexdigest() == item["request_sha256"]
        assert hashlib.sha256(result_bytes).hexdigest() == item["expected_result_sha256"]
        assert result.event_stream_hash.hex() == item["event_stream_hash"]
        assert result.final_book_hash.hex() == item["final_book_hash"]
        assert result.event_stream_hash == event_stream_hash(result.events)
        assert result.final_book_hash == book_hash(result.final_book)
        assert len(result.events) == item["event_count"]
        assert len(result.metrics) == item["metric_count"]
        assert dict(Counter(event.WhichOneof("payload") for event in result.events)) == item["event_type_counts"]
        assert request.contract_version == manifest["contract_version"]
        assert result.contract_version == manifest["contract_version"]


def test_corpus_covers_all_scenarios_event_types_and_empty_book_optionals() -> None:
    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    scenarios = {item["scenario_name"] for item in manifest["cases"]}
    event_types = {
        event_type
        for item in manifest["cases"]
        for event_type, count in item["event_type_counts"].items()
        if count > 0
    }
    empty_result_item = next(item for item in manifest["cases"] if item["case_id"] == "empty-book-seed-7")
    empty_result = exchange_pb2.SimulationResult.FromString(
        (CORPUS_ROOT / empty_result_item["expected_result_file"]).read_bytes()
    )

    assert scenarios == {
        "normal_market",
        "spoofing_like_wall",
        "layering_like",
        "quote_stuffing",
        "liquidity_evaporation",
    }
    assert event_types == {"add", "modify", "cancel", "execute", "snapshot"}
    assert not empty_result.final_book.HasField("best_bid_ticks")
    assert not empty_result.final_book.HasField("best_ask_ticks")
    assert not empty_result.final_book.HasField("mid_price_ticks_x2")
    assert not empty_result.final_book.HasField("spread_ticks")
