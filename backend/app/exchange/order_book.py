from collections import defaultdict
from dataclasses import replace

from app.exchange.schemas import Order


class OrderBook:
    def __init__(self) -> None:
        self.bids: dict[float, list[Order]] = defaultdict(list)
        self.asks: dict[float, list[Order]] = defaultdict(list)
        self.orders: dict[str, Order] = {}

    def add_limit_order(self, order: Order) -> None:
        if order.price is None:
            raise ValueError("limit order requires a price")
        levels = self.bids if order.side == "buy" else self.asks
        levels[order.price].append(order)
        self.orders[order.order_id] = order

    def add(self, order: Order) -> None:
        self.add_limit_order(order)

    def cancel_order(self, order_id: str) -> Order | None:
        order = self.orders.pop(order_id, None)
        if order is None or order.price is None:
            return None
        levels = self.bids if order.side == "buy" else self.asks
        levels[order.price] = [item for item in levels[order.price] if item.order_id != order_id]
        if not levels[order.price]:
            del levels[order.price]
        return order

    def cancel(self, order_id: str) -> Order | None:
        return self.cancel_order(order_id)

    def match_order(self, order: Order, limit_price: float | None = None) -> list[dict[str, object]]:
        opposite_levels = self.asks if order.side == "buy" else self.bids
        prices = sorted(opposite_levels) if order.side == "buy" else sorted(opposite_levels, reverse=True)
        remaining = order.quantity
        trades: list[dict[str, object]] = []

        for price in prices:
            if limit_price is not None:
                buy_too_expensive = order.side == "buy" and price > limit_price
                sell_too_cheap = order.side == "sell" and price < limit_price
                if buy_too_expensive or sell_too_cheap:
                    continue
            if remaining <= 0:
                break
            resting_orders = opposite_levels.get(price, [])
            updated_level: list[Order] = []

            for resting in resting_orders:
                if remaining <= 0:
                    updated_level.append(resting)
                    continue

                traded_quantity = min(remaining, resting.quantity)
                remaining -= traded_quantity
                trades.append(
                    {
                        "type": "trade",
                        "aggressor_order_id": order.order_id,
                        "resting_order_id": resting.order_id,
                        "aggressor_agent_id": order.agent_id,
                        "resting_agent_id": resting.agent_id,
                        "side": order.side,
                        "price": price,
                        "quantity": traded_quantity,
                        "timestamp": order.timestamp,
                    }
                )

                if traded_quantity == resting.quantity:
                    self.orders.pop(resting.order_id, None)
                else:
                    updated = replace(resting, quantity=resting.quantity - traded_quantity)
                    self.orders[updated.order_id] = updated
                    updated_level.append(updated)

            if updated_level:
                opposite_levels[price] = updated_level
            else:
                opposite_levels.pop(price, None)

        return trades

    def apply_market_order(self, order: Order) -> list[dict[str, object]]:
        if order.order_type != "market":
            raise ValueError("apply_market_order requires a market order")
        return self.match_order(order)

    def best_bid(self) -> float | None:
        return max(self.bids) if self.bids else None

    def best_ask(self) -> float | None:
        return min(self.asks) if self.asks else None

    def get_best_bid_ask(self) -> dict[str, float | None]:
        return {"best_bid": self.best_bid(), "best_ask": self.best_ask()}

    def get_l2_snapshot(self, depth: int = 5) -> dict[str, list[dict[str, float | int]]]:
        bid_prices = sorted(self.bids, reverse=True)[:depth]
        ask_prices = sorted(self.asks)[:depth]
        return {
            "bids": [{"price": price, "quantity": sum(order.quantity for order in self.bids[price])} for price in bid_prices],
            "asks": [{"price": price, "quantity": sum(order.quantity for order in self.asks[price])} for price in ask_prices],
        }

    def snapshot(self, depth: int = 5) -> dict[str, list[dict[str, float | int]]]:
        return self.get_l2_snapshot(depth)
