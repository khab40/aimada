from decimal import Decimal

from app.arena.engine import SimulationEngine
from app.contracts.determinism import decimal_to_units, midpoint_ticks_x2, quantize_metric
from app.contracts.generated.lob.exchange.v1 import exchange_pb2
from app.contracts.hashing import book_hash, event_stream_hash
from app.exchange.schemas import (
    AddOrderEvent,
    CancelOrderEvent,
    CanonicalExchangeEvent,
    ExecuteOrderEvent,
    LobSnapshotEvent,
    ModifyOrderEvent,
    OrderBookSnapshot,
    PriceLevel,
)


class ReferenceKernelError(ValueError):
    pass


class PythonReferenceKernel:
    """Protobuf boundary around the authoritative Python simulation."""

    def run(self, request: exchange_pb2.SimulationRequest) -> exchange_pb2.SimulationResult:
        _validate_request(request)
        config = request.config
        price_unit = config.price_tick_size_nanos
        quantity_unit = config.quantity_lot_size_nanos
        price_tick_size = _units_to_decimal(config.baseline_liquidity_tick_size_ticks, price_unit)
        reference_price = _units_to_decimal(config.reference_price_ticks, price_unit)
        baseline_size = _units_to_decimal(config.baseline_liquidity_base_lots, quantity_unit)
        max_quote_size = _units_to_decimal(config.max_agent_quote_lots, quantity_unit)
        engine = SimulationEngine(
            tick_interval_seconds=config.tick_interval_ns / 1_000_000_000,
            seed=request.scenario.seed,
            normal_agent_count=config.normal_agent_count,
            baseline_liquidity_levels=config.baseline_liquidity_levels,
            baseline_liquidity_base_size=float(baseline_size),
            baseline_liquidity_tick_size=float(price_tick_size),
            baseline_liquidity_reference_price=float(reference_price),
            max_agent_quote_size=float(max_quote_size),
            exchange_snapshot_depth=config.snapshot_depth,
            exchange_symbol=config.symbol,
            exchange_venue=config.venue,
        )
        if request.scenario.scenario_name not in {"", "normal_market"}:
            launch = engine.launch_scenario(request.scenario.scenario_name)
            if not launch.get("accepted"):
                raise ReferenceKernelError(str(launch.get("error") or "scenario was rejected"))

        for _ in range(request.scenario.max_ticks):
            engine.step()
            if len(engine.exchange_event_log.events) > config.max_events:
                raise ReferenceKernelError("simulation exceeded configured max_events at a completed tick boundary")

        proto_events = [
            exchange_event_to_proto(event, price_unit=price_unit, quantity_unit=quantity_unit)
            for event in engine.exchange_event_log.events
        ]
        final_book = book_to_proto(
            engine.order_book.get_snapshot(config.snapshot_depth),
            price_unit=price_unit,
            quantity_unit=quantity_unit,
        )
        return exchange_pb2.SimulationResult(
            contract_version=request.contract_version,
            run_id=request.run_id,
            events=proto_events,
            final_book=final_book,
            metrics=_metrics_to_proto(engine),
            event_stream_hash=event_stream_hash(proto_events, contract_version=request.contract_version),
            final_book_hash=book_hash(final_book),
            termination_reason=exchange_pb2.TERMINATION_REASON_COMPLETED,
        )


def exchange_event_to_proto(
    event: CanonicalExchangeEvent,
    *,
    price_unit: int,
    quantity_unit: int,
) -> exchange_pb2.ExchangeEvent:
    metadata = _metadata_to_proto(event)
    if isinstance(event, AddOrderEvent):
        return exchange_pb2.ExchangeEvent(
            metadata=metadata,
            add=exchange_pb2.AddOrder(
                order_id=event.order_id,
                agent_id=event.agent_id,
                side=_side_to_proto(event.side),
                price_ticks=_decimal_units(event.price, price_unit),
                quantity_lots=_decimal_units(event.quantity, quantity_unit),
                owner=event.owner,
            ),
        )
    if isinstance(event, ModifyOrderEvent):
        return exchange_pb2.ExchangeEvent(
            metadata=metadata,
            modify=exchange_pb2.ModifyOrder(
                order_id=event.order_id,
                agent_id=event.agent_id,
                side=_side_to_proto(event.side),
                previous_price_ticks=_decimal_units(event.previous_price, price_unit),
                previous_quantity_lots=_decimal_units(event.previous_quantity, quantity_unit),
                price_ticks=_decimal_units(event.price, price_unit),
                quantity_lots=_decimal_units(event.quantity, quantity_unit),
                priority_preserved=event.priority_preserved,
                owner=event.owner,
            ),
        )
    if isinstance(event, CancelOrderEvent):
        return exchange_pb2.ExchangeEvent(
            metadata=metadata,
            cancel=exchange_pb2.CancelOrder(
                order_id=event.order_id,
                agent_id=event.agent_id,
                side=_side_to_proto(event.side),
                price_ticks=_decimal_units(event.price, price_unit),
                quantity_lots=_decimal_units(event.quantity, quantity_unit),
                owner=event.owner,
            ),
        )
    if isinstance(event, ExecuteOrderEvent):
        return exchange_pb2.ExchangeEvent(
            metadata=metadata,
            execute=exchange_pb2.ExecuteOrder(
                execution_id=event.execution_id,
                aggressor_order_id=event.aggressor_order_id,
                resting_order_id=event.resting_order_id,
                aggressor_agent_id=event.aggressor_agent_id,
                resting_agent_id=event.resting_agent_id,
                aggressor_side=_side_to_proto(event.side),
                price_ticks=_decimal_units(event.price, price_unit),
                quantity_lots=_decimal_units(event.quantity, quantity_unit),
                aggressor_remaining_quantity_lots=_decimal_units(
                    event.aggressor_remaining_quantity,
                    quantity_unit,
                ),
                resting_remaining_quantity_lots=_decimal_units(
                    event.resting_remaining_quantity,
                    quantity_unit,
                ),
            ),
        )
    if isinstance(event, LobSnapshotEvent):
        return exchange_pb2.ExchangeEvent(
            metadata=metadata,
            snapshot=exchange_pb2.LobSnapshot(
                depth=event.depth,
                book=book_to_proto(event.book, price_unit=price_unit, quantity_unit=quantity_unit),
            ),
        )
    raise TypeError(f"unsupported canonical exchange event: {type(event).__name__}")


def book_to_proto(
    book: OrderBookSnapshot,
    *,
    price_unit: int,
    quantity_unit: int,
) -> exchange_pb2.BookSnapshot:
    result = exchange_pb2.BookSnapshot(
        bids=[_level_to_proto(level, price_unit, quantity_unit) for level in book.bids],
        asks=[_level_to_proto(level, price_unit, quantity_unit) for level in book.asks],
    )
    if book.best_bid is not None:
        result.best_bid_ticks = _decimal_units(book.best_bid, price_unit)
    if book.best_ask is not None:
        result.best_ask_ticks = _decimal_units(book.best_ask, price_unit)
    if result.HasField("best_bid_ticks") and result.HasField("best_ask_ticks"):
        result.mid_price_ticks_x2 = midpoint_ticks_x2(result.best_bid_ticks, result.best_ask_ticks)
        result.spread_ticks = result.best_ask_ticks - result.best_bid_ticks
    return result


def _validate_request(request: exchange_pb2.SimulationRequest) -> None:
    if request.contract_version != 1:
        raise ReferenceKernelError("Python reference kernel supports contract_version 1")
    if not request.run_id:
        raise ReferenceKernelError("run_id must not be empty")
    if request.scenario.max_ticks <= 0:
        raise ReferenceKernelError("scenario.max_ticks must be positive")
    if request.scenario.parameters:
        raise ReferenceKernelError("scenario parameters are not supported until their semantics are frozen")
    config = request.config
    for field_name in (
        "price_tick_size_nanos",
        "quantity_lot_size_nanos",
        "snapshot_depth",
        "max_events",
        "tick_interval_ns",
        "baseline_liquidity_tick_size_ticks",
        "max_agent_quote_lots",
    ):
        if getattr(config, field_name) <= 0:
            raise ReferenceKernelError(f"config.{field_name} must be positive")
    if not config.symbol or not config.venue:
        raise ReferenceKernelError("config symbol and venue must not be empty")


def _metadata_to_proto(event: CanonicalExchangeEvent) -> exchange_pb2.EventMetadata:
    if event.sequence is None:
        raise ReferenceKernelError("canonical event must be sequenced before Protobuf conversion")
    metadata = exchange_pb2.EventMetadata(
        schema_version=event.schema_version,
        event_id=event.event_id,
        sequence=event.sequence,
        source=(
            exchange_pb2.EVENT_SOURCE_SIMULATION
            if event.source == "simulation"
            else exchange_pb2.EVENT_SOURCE_HISTORICAL
        ),
        symbol=event.symbol,
        venue=event.venue,
    )
    _set_optional_scalar(metadata, "source_sequence", event.source_sequence)
    _set_optional_scalar(metadata, "tick", event.tick)
    _set_optional_scalar(metadata, "exchange_timestamp_ns", event.exchange_timestamp_ns)
    _set_optional_scalar(metadata, "received_timestamp_ns", event.received_timestamp_ns)
    _set_optional_scalar(metadata, "scenario_id", event.scenario_id)
    _set_optional_scalar(metadata, "scenario_name", event.scenario_name)
    _set_optional_scalar(metadata, "scenario_family", event.scenario_family)
    return metadata


def _set_optional_scalar(message: object, field_name: str, value: object | None) -> None:
    if value is not None:
        setattr(message, field_name, value)


def _level_to_proto(level: PriceLevel, price_unit: int, quantity_unit: int) -> exchange_pb2.PriceLevel:
    result = exchange_pb2.PriceLevel(
        price_ticks=_decimal_units(level.price, price_unit),
        quantity_lots=_decimal_units(level.quantity, quantity_unit),
    )
    if level.owner is not None:
        result.owner = level.owner
    return result


def _metrics_to_proto(engine: SimulationEngine) -> list[exchange_pb2.MetricValue]:
    values: dict[str, object] = {"tick": engine.clock.tick}
    features = engine.state.features
    if hasattr(features, "model_dump"):
        features = features.model_dump(mode="python")
    if isinstance(features, dict):
        values.update({f"market.{name}": value for name, value in features.items() if isinstance(value, (int, float))})
    for score in engine.state.detectors.scores:
        values[f"detector.{score.name}.confidence"] = score.confidence
    return [
        exchange_pb2.MetricValue(
            name=name,
            quantized_value=quantize_metric(str(value), decimal_scale=6),
            decimal_scale=6,
        )
        for name, value in sorted(values.items())
    ]


def _side_to_proto(side: str) -> int:
    return exchange_pb2.SIDE_BUY if side == "buy" else exchange_pb2.SIDE_SELL


def _decimal_units(value: int | float | Decimal, unit_size_nanos: int) -> int:
    return decimal_to_units(str(value), unit_size_nanos=unit_size_nanos)


def _units_to_decimal(units: int, unit_size_nanos: int) -> Decimal:
    return Decimal(units) * Decimal(unit_size_nanos) / Decimal(1_000_000_000)
