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
