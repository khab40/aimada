from dataclasses import replace

from app.exchange.order_book import OrderBook
from app.exchange.schemas import Order


class MatchingEngine:
    def __init__(self) -> None:
        self.book = OrderBook()

    def process_event(self, order: Order) -> list[dict[str, object]]:
        if order.order_type == "cancel":
            canceled = self.book.cancel_order(order.order_id)
            return [{"type": "cancel", "order_id": order.order_id, "agent_id": order.agent_id}] if canceled else []

        if order.order_type == "market":
            return self.match_market_order(order)

        events = self.match_limit_order(order)
        return events

    def submit(self, order: Order) -> list[dict[str, object]]:
        return self.process_event(order)

    def match_limit_order(self, order: Order) -> list[dict[str, object]]:
        trades = self.book.match_order(order, limit_price=order.price)
        filled_quantity = sum(int(trade["quantity"]) for trade in trades)
        remaining_quantity = order.quantity - filled_quantity
        events = list(trades)
        if remaining_quantity <= 0:
            return events

        resting_order = replace(order, quantity=remaining_quantity)
        self.book.add_limit_order(resting_order)
        events.append(
            {
                "type": "limit_order",
                "order_id": resting_order.order_id,
                "agent_id": resting_order.agent_id,
                "side": resting_order.side,
                "price": resting_order.price,
                "quantity": resting_order.quantity,
                "timestamp": resting_order.timestamp,
            }
        )
        return events

    def match_market_order(self, order: Order) -> list[dict[str, object]]:
        trades = self.book.apply_market_order(order)
        if trades:
            return trades
        return [{
            "type": "market_order_unfilled",
            "order_id": order.order_id,
            "agent_id": order.agent_id,
            "side": order.side,
            "quantity": order.quantity,
            "timestamp": order.timestamp,
        }]

    def update_book(self, order: Order) -> list[dict[str, object]]:
        return self.process_event(order)

    def snapshot(self) -> dict[str, object]:
        snapshot = self.book.get_l2_snapshot()
        best = self.book.get_best_bid_ask()
        best_bid = best["best_bid"]
        best_ask = best["best_ask"]
        mid = (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None
        spread = best_ask - best_bid if best_bid is not None and best_ask is not None else None
        return {
            **snapshot,
            **best,
            "mid": mid,
            "spread": spread,
        }
