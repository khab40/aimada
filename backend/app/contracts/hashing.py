import hashlib
import struct
import unicodedata
from collections.abc import Iterable

from app.contracts.generated.lob.exchange.v1 import exchange_pb2

EVENT_DOMAIN = b"LOB-EVENT-V1\0"
BOOK_DOMAIN = b"LOB-BOOK-V1\0"
STREAM_INIT_DOMAIN = b"LOB-STREAM-INIT-V1\0"
STREAM_STEP_DOMAIN = b"LOB-STREAM-STEP-V1\0"
SHA256_SIZE = 32


class CanonicalWriter:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def raw(self, value: bytes) -> None:
        self._buffer.extend(value)

    def boolean(self, value: bool) -> None:
        self.raw(b"\x01" if value else b"\x00")

    def u8(self, value: int) -> None:
        if value < 0 or value > 0xFF:
            raise ValueError("value does not fit uint8")
        self.raw(struct.pack(">B", value))

    def u32(self, value: int) -> None:
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError("value does not fit uint32")
        self.raw(struct.pack(">I", value))

    def u64(self, value: int) -> None:
        if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
            raise ValueError("value does not fit uint64")
        self.raw(struct.pack(">Q", value))

    def i64(self, value: int) -> None:
        if value < -(1 << 63) or value > (1 << 63) - 1:
            raise ValueError("value does not fit int64")
        self.raw(struct.pack(">q", value))

    def string(self, value: str) -> None:
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("canonical strings must already be Unicode NFC")
        encoded = value.encode("utf-8")
        self.u32(len(encoded))
        self.raw(encoded)

    def optional_u64(self, present: bool, value: int) -> None:
        self.boolean(present)
        if present:
            self.u64(value)

    def optional_i64(self, present: bool, value: int) -> None:
        self.boolean(present)
        if present:
            self.i64(value)

    def optional_string(self, present: bool, value: str) -> None:
        self.boolean(present)
        if present:
            self.string(value)

    def bytes(self) -> bytes:
        return bytes(self._buffer)


def canonical_event_bytes(event: exchange_pb2.ExchangeEvent) -> bytes:
    writer = CanonicalWriter()
    writer.raw(EVENT_DOMAIN)
    _write_metadata(writer, event.metadata)
    payload = event.WhichOneof("payload")
    if payload == "add":
        writer.u8(1)
        _write_resting_order(writer, event.add)
    elif payload == "modify":
        writer.u8(2)
        writer.string(event.modify.order_id)
        writer.string(event.modify.agent_id)
        writer.u8(event.modify.side)
        writer.i64(event.modify.previous_price_ticks)
        writer.i64(event.modify.previous_quantity_lots)
        writer.i64(event.modify.price_ticks)
        writer.i64(event.modify.quantity_lots)
        writer.boolean(event.modify.priority_preserved)
        writer.string(event.modify.owner)
    elif payload == "cancel":
        writer.u8(3)
        _write_resting_order(writer, event.cancel)
    elif payload == "execute":
        writer.u8(4)
        writer.string(event.execute.execution_id)
        writer.string(event.execute.aggressor_order_id)
        writer.string(event.execute.resting_order_id)
        writer.string(event.execute.aggressor_agent_id)
        writer.string(event.execute.resting_agent_id)
        writer.u8(event.execute.aggressor_side)
        writer.i64(event.execute.price_ticks)
        writer.i64(event.execute.quantity_lots)
        writer.i64(event.execute.aggressor_remaining_quantity_lots)
        writer.i64(event.execute.resting_remaining_quantity_lots)
    elif payload == "snapshot":
        writer.u8(5)
        writer.u32(event.snapshot.depth)
        _write_book_body(writer, event.snapshot.book)
    else:
        raise ValueError("exchange event must contain exactly one supported payload")
    return writer.bytes()


def event_hash(event: exchange_pb2.ExchangeEvent) -> bytes:
    return hashlib.sha256(canonical_event_bytes(event)).digest()


def canonical_book_bytes(book: exchange_pb2.BookSnapshot) -> bytes:
    writer = CanonicalWriter()
    writer.raw(BOOK_DOMAIN)
    _write_book_body(writer, book)
    return writer.bytes()


def book_hash(book: exchange_pb2.BookSnapshot) -> bytes:
    return hashlib.sha256(canonical_book_bytes(book)).digest()


def initial_stream_hash(contract_version: int = 1) -> bytes:
    writer = CanonicalWriter()
    writer.raw(STREAM_INIT_DOMAIN)
    writer.u32(contract_version)
    return hashlib.sha256(writer.bytes()).digest()


def advance_stream_hash(previous_hash: bytes, next_event_hash: bytes) -> bytes:
    if len(previous_hash) != SHA256_SIZE or len(next_event_hash) != SHA256_SIZE:
        raise ValueError("stream hash inputs must be 32-byte SHA-256 digests")
    return hashlib.sha256(STREAM_STEP_DOMAIN + previous_hash + next_event_hash).digest()


def event_stream_hash(
    events: Iterable[exchange_pb2.ExchangeEvent],
    *,
    contract_version: int = 1,
) -> bytes:
    digest = initial_stream_hash(contract_version)
    expected_sequence = 1
    for event in events:
        if event.metadata.schema_version != contract_version:
            raise ValueError("event schema version does not match stream contract version")
        if event.metadata.sequence != expected_sequence:
            raise ValueError(f"expected contiguous event sequence {expected_sequence}, got {event.metadata.sequence}")
        digest = advance_stream_hash(digest, event_hash(event))
        expected_sequence += 1
    return digest


def _write_metadata(writer: CanonicalWriter, metadata: exchange_pb2.EventMetadata) -> None:
    if metadata.schema_version != 1:
        raise ValueError("canonical event hashing supports schema version 1")
    if metadata.sequence == 0:
        raise ValueError("canonical event sequence must start at 1")
    writer.u32(metadata.schema_version)
    writer.string(metadata.event_id)
    writer.u64(metadata.sequence)
    writer.u8(metadata.source)
    writer.optional_u64(metadata.HasField("source_sequence"), metadata.source_sequence)
    writer.string(metadata.symbol)
    writer.string(metadata.venue)
    writer.optional_u64(metadata.HasField("tick"), metadata.tick)
    writer.optional_i64(metadata.HasField("exchange_timestamp_ns"), metadata.exchange_timestamp_ns)
    writer.optional_i64(metadata.HasField("received_timestamp_ns"), metadata.received_timestamp_ns)
    writer.optional_string(metadata.HasField("scenario_id"), metadata.scenario_id)
    writer.optional_string(metadata.HasField("scenario_name"), metadata.scenario_name)
    writer.optional_string(metadata.HasField("scenario_family"), metadata.scenario_family)


def _write_resting_order(writer: CanonicalWriter, order: object) -> None:
    writer.string(order.order_id)
    writer.string(order.agent_id)
    writer.u8(order.side)
    writer.i64(order.price_ticks)
    writer.i64(order.quantity_lots)
    writer.string(order.owner)


def _write_book_body(writer: CanonicalWriter, book: exchange_pb2.BookSnapshot) -> None:
    writer.u32(len(book.bids))
    for level in book.bids:
        _write_price_level(writer, level)
    writer.u32(len(book.asks))
    for level in book.asks:
        _write_price_level(writer, level)
    writer.optional_i64(book.HasField("best_bid_ticks"), book.best_bid_ticks)
    writer.optional_i64(book.HasField("best_ask_ticks"), book.best_ask_ticks)
    writer.optional_i64(book.HasField("mid_price_ticks_x2"), book.mid_price_ticks_x2)
    writer.optional_i64(book.HasField("spread_ticks"), book.spread_ticks)


def _write_price_level(writer: CanonicalWriter, level: exchange_pb2.PriceLevel) -> None:
    writer.i64(level.price_ticks)
    writer.i64(level.quantity_lots)
    writer.optional_string(level.HasField("owner"), level.owner)
