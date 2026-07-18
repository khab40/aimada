import pytest

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


def test_price_time_priority_matches_older_order_first_at_same_price() -> None:
    book = OrderBook()
    book.add_limit_order(Order("a-old", "maker-old", "sell", 3.0, 100.0, timestamp=1))
    book.add_limit_order(Order("a-new", "maker-new", "sell", 4.0, 100.0, timestamp=2))

    trades = book.apply_market_order(Order("m-buy", "taker", "buy", 5.0, order_type="market", timestamp=3))

    assert [trade["resting_order_id"] for trade in trades] == ["a-old", "a-new"]
    assert [trade["quantity"] for trade in trades] == [3.0, 2.0]
    assert book.orders["a-new"].quantity == 2.0
    assert book.snapshot()["asks"] == [{"price": 100.0, "quantity": 2.0}]


def test_cancel_unknown_order_is_noop() -> None:
    book = OrderBook()

    assert book.cancel_order("missing") is None
    assert book.snapshot()["bids"] == []
    assert book.snapshot()["asks"] == []


def test_same_price_modify_preserves_queue_position_and_original_timestamp() -> None:
    book = OrderBook()
    book.add_limit_order(Order("a-old", "maker-old", "sell", 3.0, 100.0, timestamp=1))
    book.add_limit_order(Order("a-new", "maker-new", "sell", 4.0, 100.0, timestamp=2))

    result = book.modify_order(
        Order("a-old", "maker-old", "sell", 6.0, 100.0, order_type="modify", timestamp=9)
    )

    assert result is not None
    before, after, priority_preserved = result
    assert before.quantity == 3.0
    assert after.quantity == 6.0
    assert after.timestamp == 1
    assert priority_preserved is True
    assert [order.order_id for order in book.asks[100.0]] == ["a-old", "a-new"]


def test_price_change_modify_loses_priority_at_the_new_level() -> None:
    book = OrderBook()
    book.add_limit_order(Order("a-existing", "maker-existing", "sell", 2.0, 101.0, timestamp=1))
    book.add_limit_order(Order("a-moving", "maker-moving", "sell", 3.0, 102.0, timestamp=2))

    result = book.modify_order(
        Order("a-moving", "maker-moving", "sell", 4.0, 101.0, order_type="modify", timestamp=8)
    )

    assert result is not None
    _, after, priority_preserved = result
    assert priority_preserved is False
    assert after.timestamp == 8
    assert 102.0 not in book.asks
    assert [order.order_id for order in book.asks[101.0]] == ["a-existing", "a-moving"]


def test_modify_rejects_side_or_agent_change_and_requires_explicit_cancel() -> None:
    book = OrderBook()
    book.add_limit_order(Order("bid-1", "maker", "buy", 2.0, 99.0))

    with pytest.raises(ValueError, match="cannot change side"):
        book.modify_order(Order("bid-1", "maker", "sell", 2.0, 99.0, order_type="modify"))
    with pytest.raises(ValueError, match="cannot change agent ownership"):
        book.modify_order(Order("bid-1", "other", "buy", 2.0, 99.0, order_type="modify"))
    with pytest.raises(ValueError, match="use cancel"):
        book.modify_order(Order("bid-1", "maker", "buy", 0.0, 99.0, order_type="modify"))

    assert book.modify_order(Order("missing", "maker", "buy", 1.0, 99.0, order_type="modify")) is None


def test_typed_snapshot_respects_depth_and_matches_dictionary_boundary() -> None:
    book = OrderBook(mid_price=100.0, levels=3, tick_size=1.0, base_size=5.0)

    snapshot = book.get_snapshot(depth=2)

    assert [level.price for level in snapshot.bids] == [99.0, 98.0]
    assert [level.price for level in snapshot.asks] == [101.0, 102.0]
    assert snapshot.mid == 100.0
    assert book.get_l2_snapshot(depth=2) == snapshot.to_dict()

    with pytest.raises(ValueError, match="depth must be positive"):
        book.get_snapshot(depth=0)


def test_agent_level_modify_replaces_only_that_agents_quantity() -> None:
    book = OrderBook()
    book.update_agent_level("bid", 99.0, 5.0, agent_id="MM_A")
    book.update_agent_level("bid", 99.0, 7.0, agent_id="MM_B")

    book.update_agent_level("bid", 99.0, 2.0, agent_id="MM_A")

    assert book.snapshot()["bids"] == [{"price": 99.0, "quantity": 9.0}]
    assert book.orders["l2-bid-99.00000000-MM_A"].quantity == 2.0
    assert book.orders["l2-bid-99.00000000-MM_B"].quantity == 7.0


def test_limit_order_without_price_is_rejected() -> None:
    book = OrderBook()

    try:
        book.add_limit_order(Order("bad", "maker", "buy", 1.0))
    except ValueError as exc:
        assert str(exc) == "limit order requires a price"
    else:
        raise AssertionError("limit order without price should fail")


def test_apply_market_order_requires_market_order_type() -> None:
    book = OrderBook()

    try:
        book.apply_market_order(Order("bad", "taker", "buy", 1.0, 100.0))
    except ValueError as exc:
        assert str(exc) == "apply_market_order requires a market order"
    else:
        raise AssertionError("non-market order should fail")


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


def test_agent_level_updates_are_additive_per_agent_at_same_price() -> None:
    book = OrderBook()

    book.update_agent_level("ask", 101.0, 2.0, agent_id="AGENT_A")
    book.update_agent_level("ask", 101.0, 3.0, agent_id="AGENT_B")
    assert book.get_l2_snapshot()["asks"][0] == {"price": 101.0, "quantity": 5.0}

    book.update_agent_level("ask", 101.0, 4.0, agent_id="AGENT_A")
    assert book.get_l2_snapshot()["asks"][0] == {"price": 101.0, "quantity": 7.0}

    book.update_agent_level("ask", 101.0, 0.0, agent_id="AGENT_A")
    assert book.get_l2_snapshot()["asks"][0] == {"price": 101.0, "quantity": 3.0}


def test_partial_cancel_recomputes_shared_level_owner() -> None:
    book = OrderBook(mid_price=100.0, levels=2, tick_size=1.0, base_size=3.5)
    book.update_agent_level(
        "ask",
        101.0,
        48.0,
        agent_id="ABUSER_01",
        owner="abuser",
        order_id="attack-wall",
    )

    assert book.get_l2_snapshot()["asks"][0]["owner"] == "abuser"

    book.cancel_order("attack-wall")

    assert book.get_l2_snapshot()["asks"][0] == {"price": 101.0, "quantity": 3.5}


def test_ensure_level_minimum_adds_only_missing_baseline_quantity() -> None:
    book = OrderBook()
    book.add_limit_order(Order("existing", "maker", "sell", 1.0, 101.0))

    book.ensure_level_minimum("ask", 101.0, 1.5, agent_id="BASELINE_MM")
    assert book.get_l2_snapshot()["asks"][0] == {"price": 101.0, "quantity": 1.5}

    book.update_agent_level("ask", 101.0, 3.0, agent_id="AGENT_A")
    book.ensure_level_minimum("ask", 101.0, 1.5, agent_id="BASELINE_MM")
    assert book.get_l2_snapshot()["asks"][0] == {"price": 101.0, "quantity": 4.0}
