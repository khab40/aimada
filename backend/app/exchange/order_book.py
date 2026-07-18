from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from app.exchange.schemas import BookSide, Order, OrderBookSnapshot, PriceLevel, Side

OrderBookMutationType = Literal["add", "modify", "cancel"]


@dataclass(frozen=True)
class OrderBookMutation:
    mutation_type: OrderBookMutationType
    before: Order | None
    after: Order | None
    priority_preserved: bool = False


OrderBookMutationListener = Callable[[OrderBookMutation], None]


class OrderBook:
    def __init__(
        self,
        mid_price: float | None = None,
        levels: int = 0,
        tick_size: float = 1.0,
        base_size: float = 10.0,
        mutation_listener: OrderBookMutationListener | None = None,
    ) -> None:
        self.bids: dict[float, list[Order]] = defaultdict(list)
        self.asks: dict[float, list[Order]] = defaultdict(list)
        self.orders: dict[str, Order] = {}
        self.level_owners: dict[tuple[BookSide, float], str] = {}
        self.mid_price: float | None = None
        self.spread: float | None = None
        self._mutation_listener = mutation_listener

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
            owner=owner,
        )
        levels[price] = [order]
        self.orders[order.order_id] = order
        self.level_owners[(book_side, price)] = owner
        self.recalculate()
        replaced = next((item for item in existing_orders if item.order_id == order.order_id), None)
        for existing in existing_orders:
            if existing.order_id != order.order_id:
                self._emit_mutation("cancel", before=existing)
        if replaced is None:
            self._emit_mutation("add", after=order)
        elif replaced != order:
            self._emit_mutation("modify", before=replaced, after=order, priority_preserved=True)

    def update_agent_level(
        self,
        side: Side | BookSide,
        price: float,
        size: float,
        *,
        agent_id: str,
        owner: str = "normal",
        order_id: str | None = None,
        timestamp: int = 0,
        scenario_id: str | None = None,
        scenario_name: str | None = None,
        scenario_family: str | None = None,
    ) -> None:
        book_side = self._normalize_side(side)
        order_id = order_id or self._agent_level_order_id(book_side, price, agent_id)
        if size <= 0:
            self.cancel_order(order_id)
            return

        levels = self._levels_for_side(book_side)
        existing_orders = levels.get(price, [])
        kept_orders: list[Order] = []
        replaced: Order | None = None
        for order in existing_orders:
            if order.order_id == order_id:
                self.orders.pop(order.order_id, None)
                replaced = order
            else:
                kept_orders.append(order)

        order = Order(
            order_id=order_id,
            agent_id=agent_id,
            side="buy" if book_side == "bid" else "sell",
            quantity=size,
            price=price,
            timestamp=timestamp,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            scenario_family=scenario_family,
            owner=owner,
        )
        levels[price] = [*kept_orders, order]
        self.orders[order.order_id] = order
        self._recompute_level_owner(book_side, price)
        self.recalculate()
        if replaced is None:
            self._emit_mutation("add", after=order)
        elif replaced != order:
            self._emit_mutation("modify", before=replaced, after=order, priority_preserved=True)

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
        removed_orders = levels.pop(price, [])
        for order in removed_orders:
            self.orders.pop(order.order_id, None)
        self.level_owners.pop((book_side, price), None)
        self.recalculate()
        for order in removed_orders:
            self._emit_mutation("cancel", before=order)

    def add_limit_order(self, order: Order) -> None:
        if order.price is None:
            raise ValueError("limit order requires a price")
        if order.quantity <= 0:
            raise ValueError("limit order quantity must be positive")
        if order.order_id in self.orders:
            raise ValueError(f"duplicate order id: {order.order_id}")
        levels = self.bids if order.side == "buy" else self.asks
        levels[order.price].append(order)
        self.orders[order.order_id] = order
        self._recompute_level_owner("bid" if order.side == "buy" else "ask", order.price)
        self.recalculate()
        self._emit_mutation("add", after=order)

    def add(self, order: Order) -> None:
        self.add_limit_order(order)

    def cancel_order(self, order_id: str) -> Order | None:
        order = self.orders.pop(order_id, None)
        if order is None or order.price is None:
            return None
        levels = self.bids if order.side == "buy" else self.asks
        levels[order.price] = [item for item in levels[order.price] if item.order_id != order_id]
        book_side = "bid" if order.side == "buy" else "ask"
        if not levels[order.price]:
            del levels[order.price]
            self.level_owners.pop((book_side, order.price), None)
        else:
            self._recompute_level_owner(book_side, order.price)
        self.recalculate()
        self._emit_mutation("cancel", before=order)
        return order

    def cancel(self, order_id: str) -> Order | None:
        return self.cancel_order(order_id)

    def modify_order(self, request: Order) -> tuple[Order, Order, bool] | None:
        """Modify a resting order and report before/after state plus priority outcome."""

        existing = self.orders.get(request.order_id)
        if existing is None:
            return None
        if request.order_type != "modify":
            raise ValueError("modify_order requires a modify order")
        if request.quantity <= 0:
            raise ValueError("modify order quantity must be positive; use cancel to remove an order")
        if request.side != existing.side:
            raise ValueError("modify order cannot change side")
        if request.agent_id != existing.agent_id:
            raise ValueError("modify order cannot change agent ownership")

        new_price = request.price if request.price is not None else existing.price
        if new_price is None or new_price <= 0:
            raise ValueError("modify order requires a positive price")
        if existing.price is None:
            raise ValueError("only resting limit orders can be modified")

        priority_preserved = new_price == existing.price
        updated = replace(
            existing,
            quantity=request.quantity,
            price=new_price,
            timestamp=existing.timestamp if priority_preserved else request.timestamp,
            scenario_id=request.scenario_id or existing.scenario_id,
            scenario_name=request.scenario_name or existing.scenario_name,
            scenario_family=request.scenario_family or existing.scenario_family,
            order_type="limit",
        )

        old_levels = self.bids if existing.side == "buy" else self.asks
        old_book_side: BookSide = "bid" if existing.side == "buy" else "ask"
        if priority_preserved:
            old_levels[existing.price] = [updated if item.order_id == existing.order_id else item for item in old_levels[existing.price]]
            self.orders[updated.order_id] = updated
            self._recompute_level_owner(old_book_side, existing.price)
        else:
            old_levels[existing.price] = [item for item in old_levels[existing.price] if item.order_id != existing.order_id]
            if not old_levels[existing.price]:
                del old_levels[existing.price]
                self.level_owners.pop((old_book_side, existing.price), None)
            else:
                self._recompute_level_owner(old_book_side, existing.price)
            new_levels = self.bids if updated.side == "buy" else self.asks
            new_levels[updated.price].append(updated)
            self.orders[updated.order_id] = updated
            self._recompute_level_owner(old_book_side, updated.price)
        self.recalculate()
        self._emit_mutation("modify", before=existing, after=updated, priority_preserved=priority_preserved)
        return existing, updated, priority_preserved

    def modify(self, request: Order) -> tuple[Order, Order, bool] | None:
        return self.modify_order(request)

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
                        "aggressor_remaining_quantity": remaining,
                        "resting_remaining_quantity": resting.quantity - traded_quantity,
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
                self._recompute_level_owner("ask" if order.side == "buy" else "bid", price)
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
        return self.get_snapshot(depth).to_dict()

    def get_snapshot(self, depth: int = 5) -> OrderBookSnapshot:
        if depth <= 0:
            raise ValueError("snapshot depth must be positive")
        bid_prices = sorted(self.bids, reverse=True)[:depth]
        ask_prices = sorted(self.asks)[:depth]
        self.recalculate()
        return OrderBookSnapshot(
            bids=[self._price_level("bid", price) for price in bid_prices],
            asks=[self._price_level("ask", price) for price in ask_prices],
            best_bid=self.best_bid(),
            best_ask=self.best_ask(),
            mid=self.mid_price,
            spread=self.spread,
        )

    def _price_level(self, side: BookSide, price: float) -> PriceLevel:
        return PriceLevel(
            price=price,
            quantity=self._level_quantity(side, price),
            owner=self.level_owners.get((side, price)),
        )

    def _recompute_level_owner(self, side: BookSide, price: float) -> None:
        orders = self._levels_for_side(side).get(price, [])
        if not orders:
            self.level_owners.pop((side, price), None)
            return
        self.level_owners[(side, price)] = next(
            (order.owner for order in orders if order.owner != "normal"),
            "normal",
        )

    def set_mutation_listener(self, listener: OrderBookMutationListener | None) -> None:
        self._mutation_listener = listener

    def _emit_mutation(
        self,
        mutation_type: OrderBookMutationType,
        *,
        before: Order | None = None,
        after: Order | None = None,
        priority_preserved: bool = False,
    ) -> None:
        if self._mutation_listener is not None:
            self._mutation_listener(
                OrderBookMutation(
                    mutation_type=mutation_type,
                    before=before,
                    after=after,
                    priority_preserved=priority_preserved,
                )
            )

    def snapshot(self, depth: int = 5) -> dict[str, object]:
        return self.get_l2_snapshot(depth)
