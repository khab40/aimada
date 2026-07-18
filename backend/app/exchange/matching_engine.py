from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Iterator

from app.exchange.event_log import EventLog
from app.exchange.order_book import OrderBook, OrderBookMutation
from app.exchange.schemas import (
    AddOrderEvent,
    CancelOrderEvent,
    CanonicalExchangeEvent,
    ExchangeEventOrigin,
    ExecuteOrderEvent,
    LobSnapshotEvent,
    ModifyOrderEvent,
    Order,
)


@dataclass(frozen=True)
class MutationContext:
    tick: int | None = None
    scenario_id: str | None = None
    scenario_name: str | None = None
    scenario_family: str | None = None


class MatchingEngine:
    def __init__(
        self,
        *,
        symbol: str = "LOB",
        venue: str = "SIM",
        source: ExchangeEventOrigin = "simulation",
        event_log: EventLog | None = None,
        book: OrderBook | None = None,
    ) -> None:
        self.book = book or OrderBook()
        self.symbol = symbol
        self.venue = venue
        self.source = source
        self.event_log = event_log or EventLog()
        self._mutation_context = MutationContext()
        self.book.set_mutation_listener(self._record_book_mutation)

    @contextmanager
    def mutation_context(
        self,
        *,
        tick: int | None = None,
        scenario_id: str | None = None,
        scenario_name: str | None = None,
        scenario_family: str | None = None,
    ) -> Iterator[None]:
        previous = self._mutation_context
        self._mutation_context = MutationContext(
            tick=tick,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            scenario_family=scenario_family,
        )
        try:
            yield
        finally:
            self._mutation_context = previous

    def process_event(self, order: Order) -> list[CanonicalExchangeEvent]:
        if order.order_type == "cancel":
            return self.cancel_order(order)
        if order.order_type == "modify":
            return self.modify_order(order)
        if order.order_type == "market":
            return self.match_market_order(order)
        return self.match_limit_order(order)

    def submit(self, order: Order) -> list[CanonicalExchangeEvent]:
        return self.process_event(order)

    def cancel_order(self, request: Order) -> list[CanonicalExchangeEvent]:
        cursor = self.event_log.next_sequence - 1
        with self._request_context(request):
            self.book.cancel_order(request.order_id)
        return self.event_log.replay_events(after_sequence=cursor)

    def modify_order(self, request: Order) -> list[CanonicalExchangeEvent]:
        cursor = self.event_log.next_sequence - 1
        with self._request_context(request):
            self.book.modify_order(request)
        return self.event_log.replay_events(after_sequence=cursor)

    def match_limit_order(self, order: Order) -> list[CanonicalExchangeEvent]:
        cursor = self.event_log.next_sequence - 1
        trades = self.book.match_order(order, limit_price=order.price)
        self._record_executions(order, trades)
        filled_quantity = sum(float(trade["quantity"]) for trade in trades)
        remaining_quantity = order.quantity - filled_quantity
        if remaining_quantity > 0:
            resting_order = replace(order, quantity=remaining_quantity)
            with self._request_context(resting_order):
                self.book.add_limit_order(resting_order)
        return self.event_log.replay_events(after_sequence=cursor)

    def match_market_order(self, order: Order) -> list[CanonicalExchangeEvent]:
        cursor = self.event_log.next_sequence - 1
        trades = self.book.apply_market_order(order)
        self._record_executions(order, trades)
        return self.event_log.replay_events(after_sequence=cursor)

    def _record_executions(self, order: Order, trades: list[dict[str, object]]) -> None:
        for trade in trades:
            event_id = self._next_event_id("execute")
            event = ExecuteOrderEvent(
                **self._event_context("execute", order, event_id=event_id),
                execution_id=event_id,
                aggressor_order_id=str(trade["aggressor_order_id"]),
                resting_order_id=str(trade["resting_order_id"]),
                aggressor_agent_id=str(trade["aggressor_agent_id"]),
                resting_agent_id=str(trade["resting_agent_id"]),
                side=order.side,
                price=float(trade["price"]),
                quantity=float(trade["quantity"]),
                aggressor_remaining_quantity=float(trade["aggressor_remaining_quantity"]),
                resting_remaining_quantity=float(trade["resting_remaining_quantity"]),
            )
            self.event_log.append(event)

    def _record_book_mutation(self, mutation: OrderBookMutation) -> None:
        order = mutation.after or mutation.before
        if order is None or order.price is None:
            raise ValueError("order-book mutation requires priced order state")
        context = self._event_context(mutation.mutation_type, order)
        if mutation.mutation_type == "add":
            event: CanonicalExchangeEvent = AddOrderEvent(
                **context,
                order_id=order.order_id,
                agent_id=order.agent_id,
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                owner=order.owner,
            )
        elif mutation.mutation_type == "cancel":
            event = CancelOrderEvent(
                **context,
                order_id=order.order_id,
                agent_id=order.agent_id,
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                owner=order.owner,
            )
        else:
            before = mutation.before
            after = mutation.after
            if before is None or after is None or before.price is None or after.price is None:
                raise ValueError("modify mutation requires before and after priced order state")
            event = ModifyOrderEvent(
                **context,
                order_id=after.order_id,
                agent_id=after.agent_id,
                side=after.side,
                previous_price=before.price,
                previous_quantity=before.quantity,
                price=after.price,
                quantity=after.quantity,
                priority_preserved=mutation.priority_preserved,
                owner=after.owner,
            )
        self.event_log.append(event)

    @contextmanager
    def _request_context(self, order: Order) -> Iterator[None]:
        with self.mutation_context(
            tick=order.timestamp,
            scenario_id=order.scenario_id,
            scenario_name=order.scenario_name,
            scenario_family=order.scenario_family,
        ):
            yield

    def _next_event_id(self, event_type: str) -> str:
        return f"{self.venue}:{event_type}:{self.event_log.next_sequence}"

    def _event_context(self, event_type: str, order: Order, *, event_id: str | None = None) -> dict[str, object]:
        context = self._mutation_context
        return {
            "event_id": event_id or self._next_event_id(event_type),
            "source": self.source,
            "symbol": self.symbol,
            "venue": self.venue,
            "tick": context.tick if context.tick is not None else order.timestamp,
            "scenario_id": context.scenario_id or order.scenario_id,
            "scenario_name": context.scenario_name or order.scenario_name,
            "scenario_family": context.scenario_family or order.scenario_family,
        }

    def update_book(self, order: Order) -> list[CanonicalExchangeEvent]:
        return self.process_event(order)

    def record_snapshot(
        self,
        *,
        tick: int,
        depth: int = 5,
        exchange_timestamp_ns: int | None = None,
        received_timestamp_ns: int | None = None,
        scenario_id: str | None = None,
        scenario_name: str | None = None,
        scenario_family: str | None = None,
    ) -> LobSnapshotEvent:
        event = LobSnapshotEvent(
            event_id=self._next_event_id("snapshot"),
            source=self.source,
            symbol=self.symbol,
            venue=self.venue,
            tick=tick,
            exchange_timestamp_ns=exchange_timestamp_ns,
            received_timestamp_ns=received_timestamp_ns,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            scenario_family=scenario_family,
            depth=depth,
            book=self.book.get_snapshot(depth),
        )
        return self.event_log.append(event)

    def snapshot(self) -> dict[str, object]:
        return self.book.get_l2_snapshot()
