from dataclasses import dataclass
from typing import ClassVar, Literal, TypeAlias, cast

Side = Literal["buy", "sell"]
BookSide = Literal["bid", "ask"]
OrderType = Literal["limit", "modify", "cancel", "market"]
ExchangeEventType = Literal["add", "modify", "cancel", "execute", "snapshot"]
ExchangeEventOrigin = Literal["simulation", "historical"]


@dataclass(frozen=True)
class Order:
    order_id: str
    agent_id: str
    side: Side
    quantity: float
    price: float | None = None
    order_type: OrderType = "limit"
    timestamp: int = 0
    scenario_id: str | None = None
    scenario_name: str | None = None
    scenario_family: str | None = None
    owner: str = "normal"


@dataclass(frozen=True)
class PriceLevel:
    price: float
    quantity: float
    owner: str | None = None

    def to_dict(self) -> dict[str, float | str]:
        data: dict[str, float | str] = {"price": self.price, "quantity": self.quantity}
        if self.owner and self.owner != "normal":
            data["owner"] = self.owner
        return data


@dataclass(frozen=True)
class OrderBookSnapshot:
    bids: list[PriceLevel]
    asks: list[PriceLevel]
    best_bid: float | None
    best_ask: float | None
    mid: float | None
    spread: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "mid": self.mid,
            "spread": self.spread,
        }


@dataclass(frozen=True, kw_only=True)
class ExchangeEvent:
    """Common envelope for canonical simulation and historical exchange events."""

    event_type: ClassVar[ExchangeEventType]
    event_id: str
    source: ExchangeEventOrigin
    symbol: str
    venue: str
    sequence: int | None = None
    source_sequence: int | None = None
    tick: int | None = None
    exchange_timestamp_ns: int | None = None
    received_timestamp_ns: int | None = None
    scenario_id: str | None = None
    scenario_name: str | None = None
    scenario_family: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        for field_name in ("event_id", "symbol", "venue"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must not be empty")
        for field_name in (
            "sequence",
            "source_sequence",
            "tick",
            "exchange_timestamp_ns",
            "received_timestamp_ns",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.sequence == 0:
            raise ValueError("sequence must start at 1 when assigned")
        if self.schema_version != 1:
            raise ValueError("unsupported exchange event schema version")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "event_id": self.event_id,
            "sequence": self.sequence,
            "source": self.source,
            "source_sequence": self.source_sequence,
            "symbol": self.symbol,
            "venue": self.venue,
            "tick": self.tick,
            "exchange_timestamp_ns": self.exchange_timestamp_ns,
            "received_timestamp_ns": self.received_timestamp_ns,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "scenario_family": self.scenario_family,
        }


@dataclass(frozen=True, kw_only=True)
class AddOrderEvent(ExchangeEvent):
    event_type: ClassVar[Literal["add"]] = "add"
    order_id: str
    agent_id: str
    side: Side
    price: float
    quantity: float
    owner: str = "normal"

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_order_state(self.order_id, self.agent_id, self.price, self.quantity)

    def to_dict(self) -> dict[str, object]:
        return {
            **super().to_dict(),
            "order_id": self.order_id,
            "agent_id": self.agent_id,
            "side": self.side,
            "price": self.price,
            "quantity": self.quantity,
            "owner": self.owner,
        }


@dataclass(frozen=True, kw_only=True)
class ModifyOrderEvent(ExchangeEvent):
    event_type: ClassVar[Literal["modify"]] = "modify"
    order_id: str
    agent_id: str
    side: Side
    previous_price: float
    previous_quantity: float
    price: float
    quantity: float
    priority_preserved: bool
    owner: str = "normal"

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_order_state(self.order_id, self.agent_id, self.previous_price, self.previous_quantity)
        _validate_order_state(self.order_id, self.agent_id, self.price, self.quantity)
        if self.priority_preserved and self.price != self.previous_price:
            raise ValueError("price-changing modifications cannot preserve priority")

    def to_dict(self) -> dict[str, object]:
        return {
            **super().to_dict(),
            "order_id": self.order_id,
            "agent_id": self.agent_id,
            "side": self.side,
            "previous_price": self.previous_price,
            "previous_quantity": self.previous_quantity,
            "price": self.price,
            "quantity": self.quantity,
            "priority_preserved": self.priority_preserved,
            "owner": self.owner,
        }


@dataclass(frozen=True, kw_only=True)
class CancelOrderEvent(ExchangeEvent):
    event_type: ClassVar[Literal["cancel"]] = "cancel"
    order_id: str
    agent_id: str
    side: Side
    price: float
    quantity: float
    owner: str = "normal"

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_order_state(self.order_id, self.agent_id, self.price, self.quantity)

    def to_dict(self) -> dict[str, object]:
        return {
            **super().to_dict(),
            "order_id": self.order_id,
            "agent_id": self.agent_id,
            "side": self.side,
            "price": self.price,
            "quantity": self.quantity,
            "owner": self.owner,
        }


@dataclass(frozen=True, kw_only=True)
class ExecuteOrderEvent(ExchangeEvent):
    event_type: ClassVar[Literal["execute"]] = "execute"
    execution_id: str
    aggressor_order_id: str
    resting_order_id: str
    aggressor_agent_id: str
    resting_agent_id: str
    side: Side
    price: float
    quantity: float
    aggressor_remaining_quantity: float
    resting_remaining_quantity: float

    def __post_init__(self) -> None:
        super().__post_init__()
        for field_name in (
            "execution_id",
            "aggressor_order_id",
            "resting_order_id",
            "aggressor_agent_id",
            "resting_agent_id",
        ):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must not be empty")
        if self.price <= 0 or self.quantity <= 0:
            raise ValueError("execution price and quantity must be positive")
        if self.aggressor_remaining_quantity < 0 or self.resting_remaining_quantity < 0:
            raise ValueError("execution remaining quantities must be non-negative")

    def to_dict(self) -> dict[str, object]:
        return {
            **super().to_dict(),
            "execution_id": self.execution_id,
            "aggressor_order_id": self.aggressor_order_id,
            "resting_order_id": self.resting_order_id,
            "aggressor_agent_id": self.aggressor_agent_id,
            "resting_agent_id": self.resting_agent_id,
            "side": self.side,
            "price": self.price,
            "quantity": self.quantity,
            "aggressor_remaining_quantity": self.aggressor_remaining_quantity,
            "resting_remaining_quantity": self.resting_remaining_quantity,
        }


@dataclass(frozen=True, kw_only=True)
class LobSnapshotEvent(ExchangeEvent):
    event_type: ClassVar[Literal["snapshot"]] = "snapshot"
    depth: int
    book: OrderBookSnapshot

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.depth <= 0:
            raise ValueError("snapshot depth must be positive")
        if len(self.book.bids) > self.depth or len(self.book.asks) > self.depth:
            raise ValueError("snapshot contains more levels than its declared depth")

    def to_dict(self) -> dict[str, object]:
        return {
            **super().to_dict(),
            "depth": self.depth,
            "book": self.book.to_dict(),
        }


CanonicalExchangeEvent: TypeAlias = (
    AddOrderEvent | ModifyOrderEvent | CancelOrderEvent | ExecuteOrderEvent | LobSnapshotEvent
)


def _validate_order_state(order_id: str, agent_id: str, price: float, quantity: float) -> None:
    if not order_id or not agent_id:
        raise ValueError("order_id and agent_id must not be empty")
    if price <= 0 or quantity <= 0:
        raise ValueError("order price and quantity must be positive")


def exchange_event_from_dict(payload: dict[str, object]) -> CanonicalExchangeEvent:
    """Deserialize and validate one canonical exchange event payload."""

    event_type = payload.get("event_type")
    common = {
        "event_id": _required_str(payload, "event_id"),
        "sequence": _optional_int(payload, "sequence"),
        "source": cast(ExchangeEventOrigin, _required_choice(payload, "source", {"simulation", "historical"})),
        "source_sequence": _optional_int(payload, "source_sequence"),
        "symbol": _required_str(payload, "symbol"),
        "venue": _required_str(payload, "venue"),
        "tick": _optional_int(payload, "tick"),
        "exchange_timestamp_ns": _optional_int(payload, "exchange_timestamp_ns"),
        "received_timestamp_ns": _optional_int(payload, "received_timestamp_ns"),
        "scenario_id": _optional_str(payload, "scenario_id"),
        "scenario_name": _optional_str(payload, "scenario_name"),
        "scenario_family": _optional_str(payload, "scenario_family"),
        "schema_version": _required_int(payload, "schema_version"),
    }
    if event_type == "add":
        return AddOrderEvent(
            **common,
            order_id=_required_str(payload, "order_id"),
            agent_id=_required_str(payload, "agent_id"),
            side=_required_side(payload),
            price=_required_number(payload, "price"),
            quantity=_required_number(payload, "quantity"),
            owner=_optional_str(payload, "owner") or "normal",
        )
    if event_type == "modify":
        return ModifyOrderEvent(
            **common,
            order_id=_required_str(payload, "order_id"),
            agent_id=_required_str(payload, "agent_id"),
            side=_required_side(payload),
            previous_price=_required_number(payload, "previous_price"),
            previous_quantity=_required_number(payload, "previous_quantity"),
            price=_required_number(payload, "price"),
            quantity=_required_number(payload, "quantity"),
            priority_preserved=_required_bool(payload, "priority_preserved"),
            owner=_optional_str(payload, "owner") or "normal",
        )
    if event_type == "cancel":
        return CancelOrderEvent(
            **common,
            order_id=_required_str(payload, "order_id"),
            agent_id=_required_str(payload, "agent_id"),
            side=_required_side(payload),
            price=_required_number(payload, "price"),
            quantity=_required_number(payload, "quantity"),
            owner=_optional_str(payload, "owner") or "normal",
        )
    if event_type == "execute":
        return ExecuteOrderEvent(
            **common,
            execution_id=_required_str(payload, "execution_id"),
            aggressor_order_id=_required_str(payload, "aggressor_order_id"),
            resting_order_id=_required_str(payload, "resting_order_id"),
            aggressor_agent_id=_required_str(payload, "aggressor_agent_id"),
            resting_agent_id=_required_str(payload, "resting_agent_id"),
            side=_required_side(payload),
            price=_required_number(payload, "price"),
            quantity=_required_number(payload, "quantity"),
            aggressor_remaining_quantity=_required_number(payload, "aggressor_remaining_quantity"),
            resting_remaining_quantity=_required_number(payload, "resting_remaining_quantity"),
        )
    if event_type == "snapshot":
        book_payload = payload.get("book")
        if not isinstance(book_payload, dict):
            raise ValueError("book must be an object")
        return LobSnapshotEvent(
            **common,
            depth=_required_int(payload, "depth"),
            book=_order_book_snapshot_from_dict(book_payload),
        )
    raise ValueError(f"unsupported exchange event type: {event_type!r}")


def _order_book_snapshot_from_dict(payload: dict[object, object]) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        bids=_price_levels_from_payload(payload.get("bids"), "bids"),
        asks=_price_levels_from_payload(payload.get("asks"), "asks"),
        best_bid=_optional_number_value(payload.get("best_bid"), "best_bid"),
        best_ask=_optional_number_value(payload.get("best_ask"), "best_ask"),
        mid=_optional_number_value(payload.get("mid"), "mid"),
        spread=_optional_number_value(payload.get("spread"), "spread"),
    )


def _price_levels_from_payload(value: object, field_name: str) -> list[PriceLevel]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    levels: list[PriceLevel] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} entries must be objects")
        levels.append(
            PriceLevel(
                price=_required_number(item, "price"),
                quantity=_required_number(item, "quantity"),
                owner=_optional_str(item, "owner"),
            )
        )
    return levels


def _required_str(payload: dict[object, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _optional_str(payload: dict[object, object], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    return value


def _required_int(payload: dict[object, object], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _optional_int(payload: dict[object, object], field_name: str) -> int | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer or null")
    return value


def _required_number(payload: dict[object, object], field_name: str) -> float:
    value = payload.get(field_name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number")
    return float(value)


def _optional_number_value(value: object, field_name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number or null")
    return float(value)


def _required_bool(payload: dict[object, object], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _required_choice(payload: dict[object, object], field_name: str, choices: set[str]) -> str:
    value = _required_str(payload, field_name)
    if value not in choices:
        raise ValueError(f"{field_name} must be one of {sorted(choices)}")
    return value


def _required_side(payload: dict[object, object]) -> Side:
    return cast(Side, _required_choice(payload, "side", {"buy", "sell"}))
