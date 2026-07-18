from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EventSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EVENT_SOURCE_UNSPECIFIED: _ClassVar[EventSource]
    EVENT_SOURCE_SIMULATION: _ClassVar[EventSource]
    EVENT_SOURCE_HISTORICAL: _ClassVar[EventSource]

class Side(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SIDE_UNSPECIFIED: _ClassVar[Side]
    SIDE_BUY: _ClassVar[Side]
    SIDE_SELL: _ClassVar[Side]

class TerminationReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TERMINATION_REASON_UNSPECIFIED: _ClassVar[TerminationReason]
    TERMINATION_REASON_COMPLETED: _ClassVar[TerminationReason]
    TERMINATION_REASON_EVENT_LIMIT: _ClassVar[TerminationReason]
    TERMINATION_REASON_TICK_LIMIT: _ClassVar[TerminationReason]
    TERMINATION_REASON_REJECTED: _ClassVar[TerminationReason]
    TERMINATION_REASON_FAILED: _ClassVar[TerminationReason]
EVENT_SOURCE_UNSPECIFIED: EventSource
EVENT_SOURCE_SIMULATION: EventSource
EVENT_SOURCE_HISTORICAL: EventSource
SIDE_UNSPECIFIED: Side
SIDE_BUY: Side
SIDE_SELL: Side
TERMINATION_REASON_UNSPECIFIED: TerminationReason
TERMINATION_REASON_COMPLETED: TerminationReason
TERMINATION_REASON_EVENT_LIMIT: TerminationReason
TERMINATION_REASON_TICK_LIMIT: TerminationReason
TERMINATION_REASON_REJECTED: TerminationReason
TERMINATION_REASON_FAILED: TerminationReason

class EventMetadata(_message.Message):
    __slots__ = ("schema_version", "event_id", "sequence", "source", "source_sequence", "symbol", "venue", "tick", "exchange_timestamp_ns", "received_timestamp_ns", "scenario_id", "scenario_name", "scenario_family")
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    VENUE_FIELD_NUMBER: _ClassVar[int]
    TICK_FIELD_NUMBER: _ClassVar[int]
    EXCHANGE_TIMESTAMP_NS_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_TIMESTAMP_NS_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FAMILY_FIELD_NUMBER: _ClassVar[int]
    schema_version: int
    event_id: str
    sequence: int
    source: EventSource
    source_sequence: int
    symbol: str
    venue: str
    tick: int
    exchange_timestamp_ns: int
    received_timestamp_ns: int
    scenario_id: str
    scenario_name: str
    scenario_family: str
    def __init__(self, schema_version: _Optional[int] = ..., event_id: _Optional[str] = ..., sequence: _Optional[int] = ..., source: _Optional[_Union[EventSource, str]] = ..., source_sequence: _Optional[int] = ..., symbol: _Optional[str] = ..., venue: _Optional[str] = ..., tick: _Optional[int] = ..., exchange_timestamp_ns: _Optional[int] = ..., received_timestamp_ns: _Optional[int] = ..., scenario_id: _Optional[str] = ..., scenario_name: _Optional[str] = ..., scenario_family: _Optional[str] = ...) -> None: ...

class PriceLevel(_message.Message):
    __slots__ = ("price_ticks", "quantity_lots", "owner")
    PRICE_TICKS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    price_ticks: int
    quantity_lots: int
    owner: str
    def __init__(self, price_ticks: _Optional[int] = ..., quantity_lots: _Optional[int] = ..., owner: _Optional[str] = ...) -> None: ...

class BookSnapshot(_message.Message):
    __slots__ = ("bids", "asks", "best_bid_ticks", "best_ask_ticks", "mid_price_ticks_x2", "spread_ticks")
    BIDS_FIELD_NUMBER: _ClassVar[int]
    ASKS_FIELD_NUMBER: _ClassVar[int]
    BEST_BID_TICKS_FIELD_NUMBER: _ClassVar[int]
    BEST_ASK_TICKS_FIELD_NUMBER: _ClassVar[int]
    MID_PRICE_TICKS_X2_FIELD_NUMBER: _ClassVar[int]
    SPREAD_TICKS_FIELD_NUMBER: _ClassVar[int]
    bids: _containers.RepeatedCompositeFieldContainer[PriceLevel]
    asks: _containers.RepeatedCompositeFieldContainer[PriceLevel]
    best_bid_ticks: int
    best_ask_ticks: int
    mid_price_ticks_x2: int
    spread_ticks: int
    def __init__(self, bids: _Optional[_Iterable[_Union[PriceLevel, _Mapping]]] = ..., asks: _Optional[_Iterable[_Union[PriceLevel, _Mapping]]] = ..., best_bid_ticks: _Optional[int] = ..., best_ask_ticks: _Optional[int] = ..., mid_price_ticks_x2: _Optional[int] = ..., spread_ticks: _Optional[int] = ...) -> None: ...

class AddOrder(_message.Message):
    __slots__ = ("order_id", "agent_id", "side", "price_ticks", "quantity_lots", "owner")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    PRICE_TICKS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    agent_id: str
    side: Side
    price_ticks: int
    quantity_lots: int
    owner: str
    def __init__(self, order_id: _Optional[str] = ..., agent_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., price_ticks: _Optional[int] = ..., quantity_lots: _Optional[int] = ..., owner: _Optional[str] = ...) -> None: ...

class ModifyOrder(_message.Message):
    __slots__ = ("order_id", "agent_id", "side", "previous_price_ticks", "previous_quantity_lots", "price_ticks", "quantity_lots", "priority_preserved", "owner")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_PRICE_TICKS_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    PRICE_TICKS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_PRESERVED_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    agent_id: str
    side: Side
    previous_price_ticks: int
    previous_quantity_lots: int
    price_ticks: int
    quantity_lots: int
    priority_preserved: bool
    owner: str
    def __init__(self, order_id: _Optional[str] = ..., agent_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., previous_price_ticks: _Optional[int] = ..., previous_quantity_lots: _Optional[int] = ..., price_ticks: _Optional[int] = ..., quantity_lots: _Optional[int] = ..., priority_preserved: _Optional[bool] = ..., owner: _Optional[str] = ...) -> None: ...

class CancelOrder(_message.Message):
    __slots__ = ("order_id", "agent_id", "side", "price_ticks", "quantity_lots", "owner")
    ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    PRICE_TICKS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    OWNER_FIELD_NUMBER: _ClassVar[int]
    order_id: str
    agent_id: str
    side: Side
    price_ticks: int
    quantity_lots: int
    owner: str
    def __init__(self, order_id: _Optional[str] = ..., agent_id: _Optional[str] = ..., side: _Optional[_Union[Side, str]] = ..., price_ticks: _Optional[int] = ..., quantity_lots: _Optional[int] = ..., owner: _Optional[str] = ...) -> None: ...

class ExecuteOrder(_message.Message):
    __slots__ = ("execution_id", "aggressor_order_id", "resting_order_id", "aggressor_agent_id", "resting_agent_id", "aggressor_side", "price_ticks", "quantity_lots", "aggressor_remaining_quantity_lots", "resting_remaining_quantity_lots")
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    AGGRESSOR_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    RESTING_ORDER_ID_FIELD_NUMBER: _ClassVar[int]
    AGGRESSOR_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    RESTING_AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    AGGRESSOR_SIDE_FIELD_NUMBER: _ClassVar[int]
    PRICE_TICKS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    AGGRESSOR_REMAINING_QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    RESTING_REMAINING_QUANTITY_LOTS_FIELD_NUMBER: _ClassVar[int]
    execution_id: str
    aggressor_order_id: str
    resting_order_id: str
    aggressor_agent_id: str
    resting_agent_id: str
    aggressor_side: Side
    price_ticks: int
    quantity_lots: int
    aggressor_remaining_quantity_lots: int
    resting_remaining_quantity_lots: int
    def __init__(self, execution_id: _Optional[str] = ..., aggressor_order_id: _Optional[str] = ..., resting_order_id: _Optional[str] = ..., aggressor_agent_id: _Optional[str] = ..., resting_agent_id: _Optional[str] = ..., aggressor_side: _Optional[_Union[Side, str]] = ..., price_ticks: _Optional[int] = ..., quantity_lots: _Optional[int] = ..., aggressor_remaining_quantity_lots: _Optional[int] = ..., resting_remaining_quantity_lots: _Optional[int] = ...) -> None: ...

class LobSnapshot(_message.Message):
    __slots__ = ("depth", "book")
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    BOOK_FIELD_NUMBER: _ClassVar[int]
    depth: int
    book: BookSnapshot
    def __init__(self, depth: _Optional[int] = ..., book: _Optional[_Union[BookSnapshot, _Mapping]] = ...) -> None: ...

class ExchangeEvent(_message.Message):
    __slots__ = ("metadata", "add", "modify", "cancel", "execute", "snapshot")
    METADATA_FIELD_NUMBER: _ClassVar[int]
    ADD_FIELD_NUMBER: _ClassVar[int]
    MODIFY_FIELD_NUMBER: _ClassVar[int]
    CANCEL_FIELD_NUMBER: _ClassVar[int]
    EXECUTE_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    metadata: EventMetadata
    add: AddOrder
    modify: ModifyOrder
    cancel: CancelOrder
    execute: ExecuteOrder
    snapshot: LobSnapshot
    def __init__(self, metadata: _Optional[_Union[EventMetadata, _Mapping]] = ..., add: _Optional[_Union[AddOrder, _Mapping]] = ..., modify: _Optional[_Union[ModifyOrder, _Mapping]] = ..., cancel: _Optional[_Union[CancelOrder, _Mapping]] = ..., execute: _Optional[_Union[ExecuteOrder, _Mapping]] = ..., snapshot: _Optional[_Union[LobSnapshot, _Mapping]] = ...) -> None: ...

class ScenarioParameter(_message.Message):
    __slots__ = ("name", "integer_value", "string_value", "boolean_value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    INTEGER_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    integer_value: int
    string_value: str
    boolean_value: bool
    def __init__(self, name: _Optional[str] = ..., integer_value: _Optional[int] = ..., string_value: _Optional[str] = ..., boolean_value: _Optional[bool] = ...) -> None: ...

class ScenarioInput(_message.Message):
    __slots__ = ("scenario_id", "scenario_name", "scenario_family", "seed", "max_ticks", "parameters")
    SCENARIO_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_NAME_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FAMILY_FIELD_NUMBER: _ClassVar[int]
    SEED_FIELD_NUMBER: _ClassVar[int]
    MAX_TICKS_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    scenario_id: str
    scenario_name: str
    scenario_family: str
    seed: int
    max_ticks: int
    parameters: _containers.RepeatedCompositeFieldContainer[ScenarioParameter]
    def __init__(self, scenario_id: _Optional[str] = ..., scenario_name: _Optional[str] = ..., scenario_family: _Optional[str] = ..., seed: _Optional[int] = ..., max_ticks: _Optional[int] = ..., parameters: _Optional[_Iterable[_Union[ScenarioParameter, _Mapping]]] = ...) -> None: ...

class SimulationConfig(_message.Message):
    __slots__ = ("symbol", "venue", "price_tick_size_nanos", "quantity_lot_size_nanos", "snapshot_depth", "max_events", "reference_price_ticks", "baseline_liquidity_levels", "baseline_liquidity_base_lots")
    SYMBOL_FIELD_NUMBER: _ClassVar[int]
    VENUE_FIELD_NUMBER: _ClassVar[int]
    PRICE_TICK_SIZE_NANOS_FIELD_NUMBER: _ClassVar[int]
    QUANTITY_LOT_SIZE_NANOS_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_DEPTH_FIELD_NUMBER: _ClassVar[int]
    MAX_EVENTS_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_PRICE_TICKS_FIELD_NUMBER: _ClassVar[int]
    BASELINE_LIQUIDITY_LEVELS_FIELD_NUMBER: _ClassVar[int]
    BASELINE_LIQUIDITY_BASE_LOTS_FIELD_NUMBER: _ClassVar[int]
    symbol: str
    venue: str
    price_tick_size_nanos: int
    quantity_lot_size_nanos: int
    snapshot_depth: int
    max_events: int
    reference_price_ticks: int
    baseline_liquidity_levels: int
    baseline_liquidity_base_lots: int
    def __init__(self, symbol: _Optional[str] = ..., venue: _Optional[str] = ..., price_tick_size_nanos: _Optional[int] = ..., quantity_lot_size_nanos: _Optional[int] = ..., snapshot_depth: _Optional[int] = ..., max_events: _Optional[int] = ..., reference_price_ticks: _Optional[int] = ..., baseline_liquidity_levels: _Optional[int] = ..., baseline_liquidity_base_lots: _Optional[int] = ...) -> None: ...

class SimulationRequest(_message.Message):
    __slots__ = ("contract_version", "run_id", "scenario", "config")
    CONTRACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    SCENARIO_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    contract_version: int
    run_id: str
    scenario: ScenarioInput
    config: SimulationConfig
    def __init__(self, contract_version: _Optional[int] = ..., run_id: _Optional[str] = ..., scenario: _Optional[_Union[ScenarioInput, _Mapping]] = ..., config: _Optional[_Union[SimulationConfig, _Mapping]] = ...) -> None: ...

class MetricValue(_message.Message):
    __slots__ = ("name", "quantized_value", "decimal_scale")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUANTIZED_VALUE_FIELD_NUMBER: _ClassVar[int]
    DECIMAL_SCALE_FIELD_NUMBER: _ClassVar[int]
    name: str
    quantized_value: int
    decimal_scale: int
    def __init__(self, name: _Optional[str] = ..., quantized_value: _Optional[int] = ..., decimal_scale: _Optional[int] = ...) -> None: ...

class SimulationResult(_message.Message):
    __slots__ = ("contract_version", "run_id", "events", "final_book", "metrics", "event_stream_hash", "final_book_hash", "termination_reason", "termination_detail")
    CONTRACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    FINAL_BOOK_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    EVENT_STREAM_HASH_FIELD_NUMBER: _ClassVar[int]
    FINAL_BOOK_HASH_FIELD_NUMBER: _ClassVar[int]
    TERMINATION_REASON_FIELD_NUMBER: _ClassVar[int]
    TERMINATION_DETAIL_FIELD_NUMBER: _ClassVar[int]
    contract_version: int
    run_id: str
    events: _containers.RepeatedCompositeFieldContainer[ExchangeEvent]
    final_book: BookSnapshot
    metrics: _containers.RepeatedCompositeFieldContainer[MetricValue]
    event_stream_hash: bytes
    final_book_hash: bytes
    termination_reason: TerminationReason
    termination_detail: str
    def __init__(self, contract_version: _Optional[int] = ..., run_id: _Optional[str] = ..., events: _Optional[_Iterable[_Union[ExchangeEvent, _Mapping]]] = ..., final_book: _Optional[_Union[BookSnapshot, _Mapping]] = ..., metrics: _Optional[_Iterable[_Union[MetricValue, _Mapping]]] = ..., event_stream_hash: _Optional[bytes] = ..., final_book_hash: _Optional[bytes] = ..., termination_reason: _Optional[_Union[TerminationReason, str]] = ..., termination_detail: _Optional[str] = ...) -> None: ...
