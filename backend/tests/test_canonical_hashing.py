import json
from pathlib import Path

import pytest

from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.hashing import (
    advance_stream_hash,
    book_hash,
    canonical_event_bytes,
    event_hash,
    event_stream_hash,
    initial_stream_hash,
)
from tests.exchange_proto_fixtures import all_event_types, sample_book

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "contracts" / "golden" / "hashing-v1.json"


def golden() -> dict[str, object]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_event_book_and_stream_hashes_match_golden_vectors() -> None:
    fixture = golden()
    events = all_event_types()
    event_hashes = [event_hash(event) for event in events]
    rolling = []
    digest = initial_stream_hash()
    for item_hash in event_hashes:
        digest = advance_stream_hash(digest, item_hash)
        rolling.append(digest)

    assert initial_stream_hash().hex() == fixture["initial_stream_hash"]
    assert [value.hex() for value in event_hashes] == fixture["event_hashes"]
    assert [value.hex() for value in rolling] == fixture["rolling_stream_hashes"]
    assert event_stream_hash(events).hex() == fixture["final_stream_hash"]
    assert book_hash(sample_book()).hex() == fixture["book_hash"]
    assert canonical_event_bytes(events[0]).hex() == fixture["first_event_canonical_bytes"]


def test_optional_presence_and_payload_changes_change_hash() -> None:
    baseline = all_event_types()[0]
    absent_tick = exchange_pb2.ExchangeEvent()
    absent_tick.CopyFrom(baseline)
    absent_tick.metadata.ClearField("tick")
    changed_quantity = exchange_pb2.ExchangeEvent()
    changed_quantity.CopyFrom(baseline)
    changed_quantity.add.quantity_lots += 1

    assert event_hash(absent_tick) != event_hash(baseline)
    assert event_hash(changed_quantity) != event_hash(baseline)


def test_stream_hash_rejects_non_contiguous_or_wrong_version_events() -> None:
    events = all_event_types()
    events[1].metadata.sequence = 3
    with pytest.raises(ValueError, match="contiguous event sequence 2"):
        event_stream_hash(events)

    events = all_event_types()
    events[0].metadata.schema_version = 2
    with pytest.raises(ValueError, match="schema version"):
        event_stream_hash(events)


def test_hashing_rejects_non_normalized_unicode() -> None:
    event = all_event_types()[0]
    event.metadata.scenario_name = "e\u0301"

    with pytest.raises(ValueError, match="Unicode NFC"):
        canonical_event_bytes(event)


def test_raw_protobuf_wire_bytes_are_not_the_canonical_hash_encoding() -> None:
    event = all_event_types()[0]

    assert event.SerializeToString(deterministic=True) != canonical_event_bytes(event)
