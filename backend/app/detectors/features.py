from dataclasses import dataclass

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

    def to_arena_features(self) -> dict[str, float]:
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
        }


def extract_features(
    *,
    book: OrderBookSnapshot,
    events: list[AgentEvent],
    previous_depth_top_n: float | None,
    tick_interval_seconds: float,
    active_scenario: AttackTrackerState | None,
    current_tick: int,
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

    normal_side_depth = max(1.0, (bid_depth + ask_depth) / max(1, len(top_bids) + len(top_asks)))
    abuser_depth = sum(
        level.quantity
        for level in [*book.bids, *book.asks]
        if level.owner == "abuser"
    )
    wall_size_ratio = round(abuser_depth / normal_side_depth, 4) if abuser_depth else 1.0

    cancel_events = [
        event for event in events
        if "cancel" in str(getattr(event, "stage", "")).lower()
        or "cancel" in str(getattr(event, "message", "")).lower()
    ]
    trade_events = [event for event in events if event.agent_id == "TAKER_01"]
    cancel_to_trade_ratio = round(len(cancel_events) / max(1, len(trade_events)), 4)

    order_lifetime_ms = 0.0
    if active_scenario:
        order_lifetime_ms = max(0.0, (current_tick - active_scenario.start_tick) * tick_interval_seconds * 1000)

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
    )


def count_events(events: list[dict[str, object]], event_type: str) -> int:
    return sum(1 for event in events if event.get("type") == event_type)


def max_quantity(events: list[dict[str, object]]) -> int:
    quantities = [int(event.get("quantity", 0)) for event in events]
    return max(quantities, default=0)


def unique_price_levels(events: list[dict[str, object]]) -> int:
    return len({event.get("price") for event in events if event.get("price") is not None})
