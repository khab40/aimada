from app.exchange.order_book import OrderBook
from app.exchange.schemas import Order


def test_order_book_tracks_best_levels() -> None:
    book = OrderBook()
    book.add(Order("b1", "agent", "buy", 10, 99.0))
    book.add(Order("b2", "agent", "buy", 10, 100.0))
    book.add(Order("a1", "agent", "sell", 10, 101.0))

    assert book.best_bid() == 100.0
    assert book.best_ask() == 101.0


def test_order_book_applies_market_order_against_best_price() -> None:
    book = OrderBook()
    book.add_limit_order(Order("a1", "maker", "sell", 10, 100.1))
    book.add_limit_order(Order("a2", "maker", "sell", 10, 100.2))

    trades = book.apply_market_order(Order("m1", "taker", "buy", 12, order_type="market"))

    assert [trade["quantity"] for trade in trades] == [10, 2]
    assert book.snapshot()["asks"][0] == {"price": 100.2, "quantity": 8}
