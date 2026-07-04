from app.exchange.matching_engine import MatchingEngine
from app.exchange.schemas import Order


def test_matching_engine_records_limit_order_event() -> None:
    engine = MatchingEngine()
    events = engine.submit(Order("o1", "agent", "buy", 5, 99.5))

    assert events[0]["type"] == "limit_order"
    assert engine.snapshot()["bids"][0]["quantity"] == 5


def test_matching_engine_market_order_updates_book() -> None:
    engine = MatchingEngine()
    engine.process_event(Order("ask-1", "maker", "sell", 7, 100.1))

    events = engine.process_event(Order("buy-1", "taker", "buy", 4, order_type="market"))

    assert events[0]["type"] == "trade"
    assert events[0]["price"] == 100.1
    assert engine.snapshot()["asks"][0]["quantity"] == 3


def test_matching_engine_preserves_fractional_partial_fill_remainder() -> None:
    engine = MatchingEngine()
    engine.submit(Order("ask-small", "maker", "sell", 0.6, 100.0))

    events = engine.submit(Order("buy-large", "taker", "buy", 1.0, 101.0))

    assert events[0]["type"] == "trade"
    assert events[0]["quantity"] == 0.6
    assert events[1]["type"] == "limit_order"
    assert events[1]["quantity"] == 0.4
    assert engine.snapshot()["bids"][0] == {"price": 101.0, "quantity": 0.4}


def test_matching_engine_cancel_removes_resting_order_and_emits_cancel() -> None:
    engine = MatchingEngine()
    engine.submit(Order("bid-1", "maker", "buy", 2.5, 99.0))

    events = engine.submit(Order("bid-1", "maker", "buy", 0.0, order_type="cancel"))

    assert events == [{
        "type": "cancel",
        "order_id": "bid-1",
        "agent_id": "maker",
        "timestamp": 0,
        "scenario_id": None,
        "scenario_name": None,
        "scenario_family": None,
    }]
    assert engine.snapshot()["bids"] == []


def test_matching_engine_unfilled_market_order_is_reported() -> None:
    engine = MatchingEngine()

    events = engine.submit(Order("empty-buy", "taker", "buy", 5.0, order_type="market"))

    assert events == [{
        "type": "market_order_unfilled",
        "order_id": "empty-buy",
        "agent_id": "taker",
        "side": "buy",
        "quantity": 5.0,
        "timestamp": 0,
        "scenario_id": None,
        "scenario_name": None,
        "scenario_family": None,
    }]
