import pytest

from app.exchange.schemas import (
    AddOrderEvent,
    CancelOrderEvent,
    ExecuteOrderEvent,
    LobSnapshotEvent,
    ModifyOrderEvent,
    OrderBookSnapshot,
    PriceLevel,
)


def event_context(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "source": "simulation",
        "symbol": "LOB",
        "venue": "SIM",
        "tick": 7,
        "scenario_id": "scenario-1",
    }


def test_all_canonical_event_types_have_a_common_serialized_envelope() -> None:
    book = OrderBookSnapshot(
        bids=[PriceLevel(price=99.0, quantity=4.0)],
        asks=[PriceLevel(price=101.0, quantity=5.0)],
        best_bid=99.0,
        best_ask=101.0,
        mid=100.0,
        spread=2.0,
    )
    events = [
        AddOrderEvent(**event_context("event-1"), order_id="o1", agent_id="a1", side="buy", price=99, quantity=4),
        ModifyOrderEvent(
            **event_context("event-2"),
            order_id="o1",
            agent_id="a1",
            side="buy",
            previous_price=99,
            previous_quantity=4,
            price=99,
            quantity=3,
            priority_preserved=True,
        ),
        CancelOrderEvent(
            **event_context("event-3"), order_id="o1", agent_id="a1", side="buy", price=99, quantity=3
        ),
        ExecuteOrderEvent(
            **event_context("event-4"),
            execution_id="execution-1",
            aggressor_order_id="buy-1",
            resting_order_id="sell-1",
            aggressor_agent_id="taker",
            resting_agent_id="maker",
            side="buy",
            price=101,
            quantity=2,
            aggressor_remaining_quantity=0,
            resting_remaining_quantity=3,
        ),
        LobSnapshotEvent(**event_context("event-5"), depth=5, book=book),
    ]

    payloads = [event.to_dict() for event in events]

    assert [payload["event_type"] for payload in payloads] == ["add", "modify", "cancel", "execute", "snapshot"]
    assert all(payload["schema_version"] == 1 for payload in payloads)
    assert all(payload["source"] == "simulation" for payload in payloads)
    assert all(payload["symbol"] == "LOB" for payload in payloads)
    assert payloads[-1]["book"] == book.to_dict()


def test_historical_event_preserves_feed_sequence_and_nanosecond_timestamps() -> None:
    event = AddOrderEvent(
        event_id="XNAS-123",
        sequence=1,
        source="historical",
        source_sequence=123,
        symbol="MSFT",
        venue="XNAS",
        exchange_timestamp_ns=1_700_000_000_000_000_001,
        received_timestamp_ns=1_700_000_000_000_000_021,
        order_id="order-9",
        agent_id="historical-feed",
        side="sell",
        price=402.5,
        quantity=100,
    )

    payload = event.to_dict()

    assert payload["source_sequence"] == 123
    assert payload["exchange_timestamp_ns"] == 1_700_000_000_000_000_001
    assert payload["received_timestamp_ns"] == 1_700_000_000_000_000_021


def test_event_schema_rejects_invalid_order_state_and_sequence() -> None:
    with pytest.raises(ValueError, match="sequence must start at 1"):
        AddOrderEvent(
            **event_context("event-invalid"),
            sequence=0,
            order_id="o1",
            agent_id="a1",
            side="buy",
            price=99,
            quantity=4,
        )

    with pytest.raises(ValueError, match="price and quantity must be positive"):
        AddOrderEvent(
            **event_context("event-invalid"),
            order_id="o1",
            agent_id="a1",
            side="buy",
            price=99,
            quantity=0,
        )


def test_price_change_cannot_claim_to_preserve_priority() -> None:
    with pytest.raises(ValueError, match="cannot preserve priority"):
        ModifyOrderEvent(
            **event_context("event-invalid"),
            order_id="o1",
            agent_id="a1",
            side="buy",
            previous_price=99,
            previous_quantity=4,
            price=100,
            quantity=4,
            priority_preserved=True,
        )
