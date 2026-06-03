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


def test_l2_market_order_call_form_consumes_visible_depth() -> None:
    book = OrderBook(mid_price=100.0, levels=2, tick_size=1.0)

    trades = book.apply_market_order("buy", 12.0)

    assert [trade["price"] for trade in trades] == [101.0, 102.0]
    assert book.get_l2_snapshot()["asks"][0] == {"price": 102.0, "quantity": 9.0}


def test_initialized_bids_are_sorted_descending() -> None:
    book = OrderBook(mid_price=100.0, levels=4, tick_size=0.5)

    bids = book.get_l2_snapshot()["bids"]

    assert [level["price"] for level in bids] == [99.5, 99.0, 98.5, 98.0]


def test_initialized_asks_are_sorted_ascending() -> None:
    book = OrderBook(mid_price=100.0, levels=4, tick_size=0.5)

    asks = book.get_l2_snapshot()["asks"]

    assert [level["price"] for level in asks] == [100.5, 101.0, 101.5, 102.0]


def test_mid_and_spread_are_recalculated_from_best_levels() -> None:
    book = OrderBook(mid_price=100.0, levels=2, tick_size=0.5)

    snapshot = book.get_l2_snapshot()

    assert snapshot["best_bid"] == 99.5
    assert snapshot["best_ask"] == 100.5
    assert snapshot["mid"] == 100.0
    assert snapshot["spread"] == 1.0


def test_large_ask_wall_insertion_updates_level_owner_and_size() -> None:
    book = OrderBook(mid_price=100.0, levels=3, tick_size=1.0)

    book.update_level("ask", 101.0, 250.0, owner="abuser")
    ask = book.get_l2_snapshot()["asks"][0]

    assert ask == {"price": 101.0, "quantity": 250.0, "owner": "abuser"}


def test_level_removal_deletes_level_and_recalculates_market_state() -> None:
    book = OrderBook(mid_price=100.0, levels=2, tick_size=1.0)

    book.remove_level("bid", 99.0)
    snapshot = book.get_l2_snapshot()

    assert [level["price"] for level in snapshot["bids"]] == [98.0]
    assert snapshot["best_bid"] == 98.0
    assert snapshot["mid"] == 99.5
    assert snapshot["spread"] == 3.0
