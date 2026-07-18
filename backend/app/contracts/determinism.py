import hashlib
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from enum import IntEnum

UINT64_MASK = (1 << 64) - 1
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1
NANOS_PER_UNIT = 1_000_000_000
STREAM_SEED_DOMAIN = b"lob-arena-prng-v1\0"


class EventPhase(IntEnum):
    AGENT = 10
    SCENARIO = 20
    BASELINE = 30
    SNAPSHOT = 40
    METRICS = 50


@dataclass(frozen=True, order=True)
class EventOrderKey:
    logical_time: int
    phase: int
    source_priority: int
    actor_id: str
    source_sequence: int
    insertion_sequence: int

    def __post_init__(self) -> None:
        for field_name in (
            "logical_time",
            "phase",
            "source_priority",
            "source_sequence",
            "insertion_sequence",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        try:
            encoded_actor = self.actor_id.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("actor_id must contain ASCII characters only") from exc
        if not encoded_actor:
            raise ValueError("actor_id must not be empty")


class SplitMix64:
    """Portable unsigned 64-bit PRNG used by both reference and candidate kernels."""

    _GAMMA = 0x9E3779B97F4A7C15
    _MIX_1 = 0xBF58476D1CE4E5B9
    _MIX_2 = 0x94D049BB133111EB

    def __init__(self, seed: int) -> None:
        self._state = seed & UINT64_MASK

    def next_u64(self) -> int:
        self._state = (self._state + self._GAMMA) & UINT64_MASK
        value = self._state
        value = ((value ^ (value >> 30)) * self._MIX_1) & UINT64_MASK
        value = ((value ^ (value >> 27)) * self._MIX_2) & UINT64_MASK
        return (value ^ (value >> 31)) & UINT64_MASK

    def next_int(self, bound: int) -> int:
        if bound <= 0 or bound > (1 << 63):
            raise ValueError("bound must be in the range 1..2^63")
        rejection_limit = (1 << 64) - ((1 << 64) % bound)
        while True:
            candidate = self.next_u64()
            if candidate < rejection_limit:
                return candidate % bound


def derive_stream_seed(root_seed: int, stream_name: str) -> int:
    if root_seed < 0 or root_seed > UINT64_MASK:
        raise ValueError("root_seed must be an unsigned 64-bit integer")
    try:
        encoded_name = stream_name.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("stream_name must contain ASCII characters only") from exc
    if not encoded_name:
        raise ValueError("stream_name must not be empty")
    payload = STREAM_SEED_DOMAIN + root_seed.to_bytes(8, "big") + encoded_name
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def decimal_to_units(value: str | int | Decimal, *, unit_size_nanos: int) -> int:
    if unit_size_nanos <= 0:
        raise ValueError("unit_size_nanos must be positive")
    scaled = Decimal(value) * NANOS_PER_UNIT / unit_size_nanos
    integral = scaled.to_integral_exact()
    if scaled != integral:
        raise ValueError(f"{value} is not an exact multiple of unit size {unit_size_nanos} nanos")
    return _require_int64(int(integral))


def quantize_metric(value: str | int | Decimal, *, decimal_scale: int) -> int:
    if decimal_scale < 0 or decimal_scale > 18:
        raise ValueError("decimal_scale must be in the range 0..18")
    scaled = (Decimal(value) * (Decimal(10) ** decimal_scale)).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
    return _require_int64(int(scaled))


def midpoint_ticks_x2(best_bid_ticks: int, best_ask_ticks: int) -> int:
    return _require_int64(best_bid_ticks + best_ask_ticks)


def simulation_event_id(venue: str, event_type: str, sequence: int) -> str:
    if sequence <= 0:
        raise ValueError("sequence must start at 1")
    for field_name, value in (("venue", venue), ("event_type", event_type)):
        try:
            encoded = value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{field_name} must contain ASCII characters only") from exc
        if not encoded or ":" in value:
            raise ValueError(f"{field_name} must be non-empty ASCII without ':'")
    return f"{venue}:{event_type.lower()}:{sequence}"


def _require_int64(value: int) -> int:
    if value < INT64_MIN or value > INT64_MAX:
        raise OverflowError("value does not fit signed int64")
    return value
