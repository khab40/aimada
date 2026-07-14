from dataclasses import dataclass
from statistics import median

from app.schemas.arena import AgentEvent, AttackTrackerState, OrderBookSnapshot


@dataclass(frozen=True)
class DetectorFeatures:
    spread_bps: float
    order_book_imbalance: float
    top_n_bid_depth: float
    top_n_ask_depth: float
    depth_change_pct: float
    wall_size_ratio: float
    order_lifetime_ms: float
    cancel_to_trade_ratio: float
    message_rate_per_sec: float
    distance_from_touch_bps: float = 0.0
    cancel_probability: float = 0.0
    execution_ratio: float = 0.0
    replenishment_rate: float = 0.0
    side_switching_rate: float = 0.0
    participant_order_linkage: float = 0.0
    linked_participant_ids: tuple[str, ...] = ()
    linked_order_ids: tuple[str, ...] = ()
    linked_event_ids: tuple[str, ...] = ()
    large_level_count: int = 0

    def to_arena_features(self) -> dict[str, float | str]:
        depth_top_n = self.top_n_bid_depth + self.top_n_ask_depth
        return {
            "spread_bps": self.spread_bps,
            "depth_top_n": depth_top_n,
            "imbalance": self.order_book_imbalance,
            "message_rate": self.message_rate_per_sec,
            "cancel_to_trade_ratio": self.cancel_to_trade_ratio,
            "order_lifetime_ms": self.order_lifetime_ms,
            "wall_size_ratio": self.wall_size_ratio,
            "depth_change_pct": self.depth_change_pct,
            "order_book_imbalance": self.order_book_imbalance,
            "top_n_bid_depth": self.top_n_bid_depth,
            "top_n_ask_depth": self.top_n_ask_depth,
            "message_rate_per_sec": self.message_rate_per_sec,
            "distance_from_touch_bps": self.distance_from_touch_bps,
            "cancel_probability": self.cancel_probability,
            "execution_ratio": self.execution_ratio,
            "replenishment_rate": self.replenishment_rate,
            "side_switching_rate": self.side_switching_rate,
            "participant_order_linkage": self.participant_order_linkage,
            "linked_participant_ids": ",".join(self.linked_participant_ids),
            "linked_order_ids": ",".join(self.linked_order_ids),
            "linked_event_ids": ",".join(self.linked_event_ids),
            "large_level_count": float(self.large_level_count),
        }


def extract_features(
    *,
    book: OrderBookSnapshot,
    events: list[AgentEvent],
    previous_depth_top_n: float | None,
    tick_interval_seconds: float,
    active_scenario: AttackTrackerState | None,
    current_tick: int,
    order_first_seen_ticks: dict[str, int] | None = None,
    top_n: int = 5,
) -> DetectorFeatures:
    top_bids = book.bids[:top_n]
    top_asks = book.asks[:top_n]
    bid_depth = round(sum(level.quantity for level in top_bids), 4)
    ask_depth = round(sum(level.quantity for level in top_asks), 4)
    total_depth = bid_depth + ask_depth
    imbalance = round((bid_depth - ask_depth) / total_depth, 4) if total_depth else 0.0

    spread_bps = 0.0
    if book.mid and book.spread is not None:
        spread_bps = round((book.spread / book.mid) * 10_000, 4)

    depth_change_pct = 0.0
    if previous_depth_top_n and previous_depth_top_n > 0:
        depth_change_pct = round(((total_depth - previous_depth_top_n) / previous_depth_top_n) * 100, 4)

    visible_levels = [("bid", level) for level in top_bids] + [("ask", level) for level in top_asks]
    largest_side, largest_level = max(visible_levels, key=lambda item: item[1].quantity, default=("bid", None))
    nearby_quantities = [level.quantity for side, level in visible_levels if side == largest_side and level is not largest_level]
    nearby_size = median(nearby_quantities) if nearby_quantities else 1.0
    wall_size_ratio = round(largest_level.quantity / max(nearby_size, 0.0001), 4) if largest_level else 1.0
    large_level_count = sum(
        level.quantity >= nearby_size * 1.5
        for side, level in visible_levels
        if side == largest_side
    )
    touch = book.best_bid if largest_side == "bid" else book.best_ask
    distance_from_touch_bps = 0.0
    if largest_level and touch is not None and book.mid:
        distance_from_touch_bps = round(abs(largest_level.price - touch) / book.mid * 10_000, 4)

    cancel_events = [
        event for event in events
        if "cancel" in str(getattr(event, "stage", "")).lower()
        or "cancel" in str(getattr(event, "message", "")).lower()
    ]
    trade_events = [event for event in events if event.type == "trade" or "execut" in str(getattr(event, "message", "")).lower()]
    placement_events = [
        event
        for event in events
        if any(token in str(getattr(event, "message", "")).lower() for token in ("placed", "updated", "maintained"))
    ]
    cancel_to_trade_ratio = round(len(cancel_events) / max(1, len(trade_events)), 4)

    tracker = order_first_seen_ticks if order_first_seen_ticks is not None else {}
    completed_lifetimes: list[float] = []
    for event in events:
        order_id = event.order_id
        if not order_id:
            continue
        if event in cancel_events or event in trade_events:
            first_tick = tracker.pop(order_id, None)
            if first_tick is not None:
                completed_lifetimes.append((current_tick - first_tick) * tick_interval_seconds * 1000)
        else:
            tracker.setdefault(order_id, current_tick)
    active_lifetimes = [
        (current_tick - first_tick) * tick_interval_seconds * 1000
        for first_tick in tracker.values()
    ]
    observed_lifetimes = [*completed_lifetimes, *active_lifetimes]
    order_lifetime_ms = max(observed_lifetimes, default=0.0)

    linked_participants = tuple(sorted({event.agent_id for event in events if event.agent_id}))
    linked_orders = tuple(sorted({event.order_id for event in events if event.order_id}))
    linked_events_ids = tuple(sorted({event.event_id for event in events if event.event_id}))
    linked_events = sum(1 for event in events if event.agent_id or event.order_id)
    participant_order_linkage = linked_events / len(events) if events else 0.0
    cancel_probability = len(cancel_events) / max(1, len(cancel_events) + len(trade_events))
    execution_ratio = len(trade_events) / max(1, len(placement_events))
    replenishments = sum(
        1
        for event in events
        if any(token in str(getattr(event, "message", "")).lower() for token in ("maintained", "replenish", "updated"))
    )
    replenishment_rate = replenishments / max(1, len(placement_events))
    sides_by_participant: dict[str, list[str]] = {}
    for event in events:
        if event.agent_id and event.side:
            sides_by_participant.setdefault(event.agent_id, []).append(event.side)
    switches = sum(
        sum(left != right for left, right in zip(sides, sides[1:]))
        for sides in sides_by_participant.values()
    )
    side_observations = sum(max(0, len(sides) - 1) for sides in sides_by_participant.values())

    return DetectorFeatures(
        spread_bps=spread_bps,
        order_book_imbalance=imbalance,
        top_n_bid_depth=bid_depth,
        top_n_ask_depth=ask_depth,
        depth_change_pct=depth_change_pct,
        wall_size_ratio=wall_size_ratio,
        order_lifetime_ms=round(order_lifetime_ms, 4),
        cancel_to_trade_ratio=cancel_to_trade_ratio,
        message_rate_per_sec=round(len(events) / tick_interval_seconds, 4),
        distance_from_touch_bps=distance_from_touch_bps,
        cancel_probability=round(cancel_probability, 4),
        execution_ratio=round(execution_ratio, 4),
        replenishment_rate=round(replenishment_rate, 4),
        side_switching_rate=round(switches / max(1, side_observations), 4),
        participant_order_linkage=round(participant_order_linkage, 4),
        linked_participant_ids=linked_participants,
        linked_order_ids=linked_orders,
        linked_event_ids=linked_events_ids,
        large_level_count=large_level_count,
    )


def count_events(events: list[dict[str, object]], event_type: str) -> int:
    return sum(1 for event in events if event.get("type") == event_type)


def max_quantity(events: list[dict[str, object]]) -> int:
    quantities = [int(event.get("quantity", 0)) for event in events]
    return max(quantities, default=0)


def unique_price_levels(events: list[dict[str, object]]) -> int:
    return len({event.get("price") for event in events if event.get("price") is not None})
