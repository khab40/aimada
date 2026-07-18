from typing import Any

from app.schemas.arena import (
    AgentEvent,
    ArenaState,
    AttackTrackerState,
    DetectorScores,
    DetectorScore,
    ExchangeEventRecord,
    Incident,
    MarketFeatures,
    OrderBookSnapshot,
    PriceLevel,
)


def empty_detector_scores() -> DetectorScores:
    return DetectorScores(
        scores=[
            DetectorScore(name="spoofing_like", confidence=0.0, alert=False, severity="low"),
            DetectorScore(name="layering_like", confidence=0.0, alert=False, severity="low"),
            DetectorScore(name="quote_stuffing", confidence=0.0, alert=False, severity="low"),
            DetectorScore(name="liquidity_shock", confidence=0.0, alert=False, severity="low"),
        ],
        alerts=[],
    )


def default_market_features(book: OrderBookSnapshot) -> MarketFeatures:
    spread_bps = 0.0
    if book.mid and book.spread is not None:
        spread_bps = (book.spread / book.mid) * 10_000

    bid_depth = sum(level.quantity for level in book.bids[:5])
    ask_depth = sum(level.quantity for level in book.asks[:5])
    total_depth = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / total_depth if total_depth else 0.0

    return MarketFeatures(
        spread_bps=round(spread_bps, 4),
        depth_top_n=round(total_depth, 4),
        imbalance=round(imbalance, 4),
        message_rate=0.0,
        cancel_to_trade_ratio=0.0,
        order_lifetime_ms=0.0,
        wall_size_ratio=1.0,
        depth_change_pct=0.0,
    )


def arena_state_from_book(
    *,
    tick: int,
    running: bool,
    book: OrderBookSnapshot,
    events: list[AgentEvent] | None = None,
    exchange_events: list[ExchangeEventRecord] | None = None,
    features: dict[str, Any] | MarketFeatures | None = None,
    active_agents: list[str] | None = None,
    active_scenario: AttackTrackerState | None = None,
    detectors: DetectorScores | None = None,
    incidents: list[Incident] | None = None,
) -> ArenaState:
    return ArenaState(
        tick=tick,
        running=running,
        events=events or [],
        exchange_events=exchange_events or [],
        book=book,
        best_bid=book.best_bid,
        best_ask=book.best_ask,
        mid=book.mid,
        spread=book.spread,
        active_agents=active_agents or ["MM_01", "NOISE_01", "TAKER_01"],
        active_scenario=active_scenario,
        detectors=detectors or empty_detector_scores(),
        incidents=incidents or [],
        features=features or default_market_features(book),
    )


def order_book_snapshot_from_dict(snapshot: dict[str, object]) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        bids=[PriceLevel(**level) for level in snapshot["bids"]],
        asks=[PriceLevel(**level) for level in snapshot["asks"]],
        best_bid=snapshot["best_bid"],
        best_ask=snapshot["best_ask"],
        mid=snapshot["mid"],
        spread=snapshot["spread"],
    )
