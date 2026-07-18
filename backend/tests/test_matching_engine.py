from app.exchange.matching_engine import MatchingEngine
from app.exchange.schemas import AddOrderEvent, CancelOrderEvent, ExecuteOrderEvent, LobSnapshotEvent, ModifyOrderEvent, Order


def test_matching_engine_records_sequenced_add_event() -> None:
    engine = MatchingEngine()
    events = engine.submit(Order("o1", "agent", "buy", 5, 99.5))

    assert isinstance(events[0], AddOrderEvent)
    assert events[0].sequence == 1
    assert events[0].quantity == 5
    assert engine.event_log.events == tuple(events)
    assert engine.snapshot()["bids"][0]["quantity"] == 5


def test_matching_engine_market_order_emits_execution_and_updates_book() -> None:
    engine = MatchingEngine()
    engine.process_event(Order("ask-1", "maker", "sell", 7, 100.1))

    events = engine.process_event(Order("buy-1", "taker", "buy", 4, order_type="market"))

    assert isinstance(events[0], ExecuteOrderEvent)
    assert events[0].price == 100.1
    assert events[0].quantity == 4
    assert events[0].aggressor_remaining_quantity == 0
    assert events[0].resting_remaining_quantity == 3
    assert engine.snapshot()["asks"][0]["quantity"] == 3


def test_matching_engine_preserves_fractional_partial_fill_remainder() -> None:
    engine = MatchingEngine()
    engine.submit(Order("ask-small", "maker", "sell", 0.6, 100.0))

    events = engine.submit(Order("buy-large", "taker", "buy", 1.0, 101.0))

    assert isinstance(events[0], ExecuteOrderEvent)
    assert events[0].quantity == 0.6
    assert isinstance(events[1], AddOrderEvent)
    assert events[1].quantity == 0.4
    assert [event.sequence for event in events] == [2, 3]
    assert engine.snapshot()["bids"][0] == {"price": 101.0, "quantity": 0.4}


def test_matching_engine_cancel_uses_actual_resting_state() -> None:
    engine = MatchingEngine()
    engine.submit(Order("bid-1", "maker", "buy", 2.5, 99.0))

    events = engine.submit(Order("bid-1", "requester", "sell", 0.0, order_type="cancel", timestamp=4))

    assert len(events) == 1
    assert isinstance(events[0], CancelOrderEvent)
    assert events[0].agent_id == "maker"
    assert events[0].side == "buy"
    assert events[0].price == 99.0
    assert events[0].quantity == 2.5
    assert events[0].tick == 4
    assert engine.snapshot()["bids"] == []


def test_matching_engine_emits_modify_event_with_before_and_after_state() -> None:
    engine = MatchingEngine()
    engine.submit(Order("bid-1", "maker", "buy", 2.5, 99.0, timestamp=1))

    events = engine.submit(Order("bid-1", "maker", "buy", 4.0, 99.0, order_type="modify", timestamp=3))

    assert len(events) == 1
    assert isinstance(events[0], ModifyOrderEvent)
    assert events[0].previous_quantity == 2.5
    assert events[0].quantity == 4.0
    assert events[0].priority_preserved is True
    assert events[0].sequence == 2


def test_unfilled_market_and_unknown_cancel_or_modify_emit_no_exchange_event() -> None:
    engine = MatchingEngine()

    assert engine.submit(Order("empty-buy", "taker", "buy", 5.0, order_type="market")) == []
    assert engine.submit(Order("missing", "maker", "buy", 0.0, order_type="cancel")) == []
    assert engine.submit(Order("missing", "maker", "buy", 1.0, 99.0, order_type="modify")) == []
    assert engine.event_log.events == ()


def test_matching_engine_records_depth_limited_snapshot_checkpoint() -> None:
    engine = MatchingEngine(symbol="MSFT", venue="SIM-X")
    engine.book.initialize(mid_price=100.0, levels=3, tick_size=1.0, base_size=5.0)
    engine.submit(Order("agent-bid", "maker", "buy", 2.0, 99.5, timestamp=7))

    event = engine.record_snapshot(tick=7, depth=2, scenario_id="scenario-1")

    assert isinstance(event, LobSnapshotEvent)
    assert event.sequence == 8
    assert event.symbol == "MSFT"
    assert event.venue == "SIM-X"
    assert event.tick == 7
    assert event.depth == 2
    assert len(event.book.bids) == 2
    assert len(event.book.asks) == 2
    assert engine.event_log.events[-1] is event
