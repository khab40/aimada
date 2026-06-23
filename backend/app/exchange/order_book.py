from collections import defaultdict
from dataclasses import replace

from app.exchange.schemas import BookSide, Order, PriceLevel, Side


class OrderBook:
    def __init__(
        self,
        mid_price: float | None = None,
        levels: int = 0,
        tick_size: float = 1.0,
        base_size: float = 10.0,
    ) -> None:
        self.bids: dict[float, list[Order]] = defaultdict(list)
        self.asks: dict[float, list[Order]] = defaultdict(list)
        self.orders: dict[str, Order] = {}
        self.level_owners: dict[tuple[BookSide, float], str] = {}
        self.mid_price: float | None = None
        self.spread: float | None = None

        if mid_price is not None and levels > 0:
            self.initialize(mid_price=mid_price, levels=levels, tick_size=tick_size, base_size=base_size)

    def initialize(
        self,
        mid_price: float,
        levels: int,
        tick_size: float = 1.0,
        base_size: float = 10.0,
        owner: str = "normal",
    ) -> None:
        self.bids.clear()
        self.asks.clear()
        self.orders.clear()
        self.level_owners.clear()

        for index in range(levels):
            distance = index + 1
            size = base_size + index
            self.update_level("bid", mid_price - distance * tick_size, size, owner)
            self.update_level("ask", mid_price + distance * tick_size, size, owner)

        self.recalculate()

    def _normalize_side(self, side: Side | BookSide) -> BookSide:
        if side in {"buy", "bid"}:
            return "bid"
        if side in {"sell", "ask"}:
            return "ask"
        raise ValueError(f"unknown book side: {side}")

    def _levels_for_side(self, side: Side | BookSide) -> dict[float, list[Order]]:
        book_side = self._normalize_side(side)
        return self.bids if book_side == "bid" else self.asks

    def _synthetic_order_id(self, side: BookSide, price: float) -> str:
        return f"l2-{side}-{price:.8f}"

    def _agent_level_order_id(self, side: BookSide, price: float, agent_id: str) -> str:
        return f"l2-{side}-{price:.8f}-{agent_id}"

    def _level_quantity(self, side: Side | BookSide, price: float) -> float:
        levels = self._levels_for_side(side)
        return sum(order.quantity for order in levels.get(price, []))

    def recalculate(self) -> None:
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        if best_bid is None or best_ask is None:
            self.mid_price = None
            self.spread = None
            return
        self.mid_price = (best_bid + best_ask) / 2
        self.spread = best_ask - best_bid

    def update_level(self, side: Side | BookSide, price: float, size: float, owner: str = "normal") -> None:
        book_side = self._normalize_side(side)
        if size <= 0:
            self.remove_level(book_side, price)
            return

        levels = self._levels_for_side(book_side)
        existing_orders = levels.get(price, [])
        for order in existing_orders:
            self.orders.pop(order.order_id, None)

        order = Order(
            order_id=self._synthetic_order_id(book_side, price),
            agent_id=owner,
            side="buy" if book_side == "bid" else "sell",
            quantity=size,
            price=price,
        )
        levels[price] = [order]
        self.orders[order.order_id] = order
        self.level_owners[(book_side, price)] = owner
        self.recalculate()

    def update_agent_level(
        self,
        side: Side | BookSide,
        price: float,
        size: float,
        *,
        agent_id: str,
        owner: str = "normal",
    ) -> None:
        book_side = self._normalize_side(side)
        order_id = self._agent_level_order_id(book_side, price, agent_id)
        if size <= 0:
            self.cancel_order(order_id)
            return

        levels = self._levels_for_side(book_side)
        existing_orders = levels.get(price, [])
        kept_orders: list[Order] = []
        for order in existing_orders:
            if order.order_id == order_id:
                self.orders.pop(order.order_id, None)
            else:
                kept_orders.append(order)

        order = Order(
            order_id=order_id,
            agent_id=agent_id,
            side="buy" if book_side == "bid" else "sell",
            quantity=size,
            price=price,
        )
        levels[price] = [*kept_orders, order]
        self.orders[order.order_id] = order
        existing_owner = self.level_owners.get((book_side, price))
        if owner != "normal" or existing_owner is None:
            self.level_owners[(book_side, price)] = owner
        self.recalculate()

    def ensure_level_minimum(
        self,
        side: Side | BookSide,
        price: float,
        minimum_size: float,
        *,
        agent_id: str,
        owner: str = "normal",
    ) -> None:
        book_side = self._normalize_side(side)
        order_id = self._agent_level_order_id(book_side, price, agent_id)
        levels = self._levels_for_side(book_side)
        current_without_agent = sum(
            order.quantity for order in levels.get(price, []) if order.order_id != order_id
        )
        agent_size = max(0.0, round(minimum_size - current_without_agent, 6))
        self.update_agent_level(book_side, price, agent_size, agent_id=agent_id, owner=owner)

    def remove_level(self, side: Side | BookSide, price: float) -> None:
        book_side = self._normalize_side(side)
        levels = self._levels_for_side(book_side)
        for order in levels.pop(price, []):
            self.orders.pop(order.order_id, None)
        self.level_owners.pop((book_side, price), None)
        self.recalculate()

    def add_limit_order(self, order: Order) -> None:
        if order.price is None:
            raise ValueError("limit order requires a price")
        levels = self.bids if order.side == "buy" else self.asks
        levels[order.price].append(order)
        self.orders[order.order_id] = order
        self.level_owners.setdefault(("bid" if order.side == "buy" else "ask", order.price), "normal")
        self.recalculate()

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
            self.level_owners.pop(("bid" if order.side == "buy" else "ask", order.price), None)
        self.recalculate()
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
                        "scenario_id": order.scenario_id or resting.scenario_id,
                        "scenario_name": order.scenario_name or resting.scenario_name,
                        "scenario_family": order.scenario_family or resting.scenario_family,
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
                self.level_owners.pop(("ask" if order.side == "buy" else "bid", price), None)

        self.recalculate()
        return trades

    def apply_market_order(self, order_or_side: Order | Side, quantity: float | None = None) -> list[dict[str, object]]:
        if isinstance(order_or_side, Order):
            if order_or_side.order_type != "market":
                raise ValueError("apply_market_order requires a market order")
            return self.match_order(order_or_side)

        if quantity is None:
            raise ValueError("quantity is required when applying a market order by side")
        order = Order(
            order_id=f"market-{order_or_side}-{len(self.orders) + 1}",
            agent_id="market_order",
            side=order_or_side,
            quantity=quantity,
            order_type="market",
        )
        return self.match_order(order)

    def best_bid(self) -> float | None:
        return max(self.bids) if self.bids else None

    def best_ask(self) -> float | None:
        return min(self.asks) if self.asks else None

    def get_best_bid_ask(self) -> dict[str, float | None]:
        return {"best_bid": self.best_bid(), "best_ask": self.best_ask()}

    def get_l2_snapshot(self, depth: int = 5) -> dict[str, object]:
        bid_prices = sorted(self.bids, reverse=True)[:depth]
        ask_prices = sorted(self.asks)[:depth]
        self.recalculate()
        return {
            "bids": [self._price_level("bid", price).to_dict() for price in bid_prices],
            "asks": [self._price_level("ask", price).to_dict() for price in ask_prices],
            "best_bid": self.best_bid(),
            "best_ask": self.best_ask(),
            "mid": self.mid_price,
            "spread": self.spread,
        }

    def _price_level(self, side: BookSide, price: float) -> PriceLevel:
        return PriceLevel(
            price=price,
            quantity=self._level_quantity(side, price),
            owner=self.level_owners.get((side, price)),
        )

    def snapshot(self, depth: int = 5) -> dict[str, object]:
        return self.get_l2_snapshot(depth)
