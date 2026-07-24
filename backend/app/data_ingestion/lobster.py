import csv
import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from itertools import zip_longest
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from app.data_ingestion.models import (
    DatasetFile,
    DatasetManifest,
    LobsterCandidate,
    ValidationReport,
    format_milliseconds,
)

LOBSTER_FILENAME = re.compile(
    r"^(?P<symbol>.+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<start>\d+)_(?P<end>\d+)_"
    r"(?P<kind>message|orderbook)_(?P<depth>\d+)\.csv$",
    re.IGNORECASE,
)
EVENT_KINDS = {
    1: "ADD",
    2: "PARTIAL_CANCEL",
    3: "DELETE",
    4: "VISIBLE_EXECUTION",
    5: "HIDDEN_EXECUTION",
    6: "CROSS_TRADE",
    7: "TRADING_HALT",
}
DUMMY_ASK_PRICE = 9_999_999_999
DUMMY_BID_PRICE = -9_999_999_999
TIMESTAMP_SERIALIZATION_TOLERANCE_NS = Decimal("0.01")


@dataclass(frozen=True)
class ParsedMessage:
    timestamp_ns_since_midnight: int
    source_event_code: int
    event_kind: str
    source_order_id: int
    size: int
    price_x10000: int
    direction: int
    book_side: str | None
    aggressor_side: str | None
    halt_state: str | None

    def as_dict(self, *, sequence: int, symbol: str, trade_date: str) -> dict[str, object]:
        return {
            "source_sequence": sequence,
            "timestamp_ns_since_midnight": self.timestamp_ns_since_midnight,
            "event_kind": self.event_kind,
            "source_event_code": self.source_event_code,
            "source_order_id": self.source_order_id,
            "size": self.size,
            "price_x10000": self.price_x10000,
            "direction": self.direction,
            "book_side": self.book_side,
            "aggressor_side": self.aggressor_side,
            "halt_state": self.halt_state,
            "symbol": symbol,
            "trade_date": trade_date,
        }


def parse_message(row: list[str], *, line_number: int) -> ParsedMessage:
    if len(row) != 6:
        raise ValueError(f"message line {line_number}: expected 6 columns, found {len(row)}")
    try:
        timestamp = Decimal(row[0].strip())
        timestamp_ns_decimal = timestamp * Decimal(1_000_000_000)
        timestamp_ns_rounded = timestamp_ns_decimal.to_integral_value(rounding=ROUND_HALF_EVEN)
        # Some LOBSTER files contain tiny sub-nanosecond tails introduced by
        # floating-point serialization. Tolerate that noise while continuing
        # to reject genuinely higher-precision timestamps.
        if abs(timestamp_ns_decimal - timestamp_ns_rounded) > TIMESTAMP_SERIALIZATION_TOLERANCE_NS:
            raise ValueError("timestamp precision exceeds nanoseconds")
        timestamp_ns = int(timestamp_ns_rounded)
        event_code = int(row[1])
        order_id = int(row[2])
        size = int(row[3])
        price = int(row[4])
        direction = int(row[5])
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"message line {line_number}: invalid numeric value: {exc}") from exc
    if not 0 <= timestamp_ns < 86_400 * 1_000_000_000:
        raise ValueError(f"message line {line_number}: timestamp is outside the trading day")
    if event_code not in EVENT_KINDS:
        raise ValueError(f"message line {line_number}: unsupported event code {event_code}")
    if order_id < 0 or size < 0:
        raise ValueError(f"message line {line_number}: order id and size must be non-negative")
    if event_code == 7:
        if order_id != 0 or size != 0 or price not in {-1, 0, 1} or direction != -1:
            raise ValueError(f"message line {line_number}: invalid trading-halt sentinel")
        halt_state = {-1: "HALTED", 0: "QUOTE_RESUME", 1: "TRADING_RESUMED"}[price]
        book_side = None
    else:
        if size == 0:
            raise ValueError(f"message line {line_number}: non-halt size must be positive")
        if event_code in {1, 2, 3, 4} and order_id == 0:
            raise ValueError(f"message line {line_number}: visible order event requires a positive order id")
        if price <= 0:
            raise ValueError(f"message line {line_number}: price_x10000 must be positive")
        if direction not in {-1, 1}:
            raise ValueError(f"message line {line_number}: direction must be -1 or 1")
        halt_state = None
        book_side = "BUY" if direction == 1 else "SELL"
    aggressor_side = None
    if event_code in {4, 5} and book_side is not None:
        aggressor_side = "SELL" if book_side == "BUY" else "BUY"
    return ParsedMessage(
        timestamp_ns_since_midnight=timestamp_ns,
        source_event_code=event_code,
        event_kind=EVENT_KINDS[event_code],
        source_order_id=order_id,
        size=size,
        price_x10000=price,
        direction=direction,
        book_side=book_side,
        aggressor_side=aggressor_side,
        halt_state=halt_state,
    )


def discover_candidates(raw_dir: Path, processed_dir: Path) -> list[LobsterCandidate]:
    raw_root = raw_dir.resolve()
    if not raw_root.exists():
        return []
    grouped: dict[tuple[str, str, str, int, int, int], dict[str, list[Path]]] = {}
    for path in sorted(raw_root.rglob("*.csv")):
        resolved_path = path.resolve()
        if not resolved_path.is_relative_to(raw_root) or not resolved_path.is_file():
            continue
        match = LOBSTER_FILENAME.fullmatch(path.name)
        if not match:
            continue
        key = (
            path.parent.relative_to(raw_root).as_posix(),
            match.group("symbol").upper(),
            match.group("date"),
            int(match.group("start")),
            int(match.group("end")),
            int(match.group("depth")),
        )
        grouped.setdefault(key, {"message": [], "orderbook": []})[match.group("kind").lower()].append(path)

    candidates: list[LobsterCandidate] = []
    imported = {manifest.dataset_id: manifest for manifest, _ in iter_manifests(processed_dir)}
    for key, paths in grouped.items():
        _relative_parent, symbol, trade_date, start, end, depth = key
        candidate_id = candidate_identifier(key)
        errors: list[str] = []
        try:
            datetime.strptime(trade_date, "%Y-%m-%d")
        except ValueError:
            errors.append("invalid trade date")
        if not 0 <= start < end <= 86_400_000:
            errors.append("time range must be within one day and start before end")
        if depth <= 0:
            errors.append("depth must be positive")
        for kind in ("message", "orderbook"):
            if not paths[kind]:
                errors.append(f"missing {kind} file")
            elif len(paths[kind]) > 1:
                errors.append(f"multiple {kind} files")
        message = paths["message"][0] if len(paths["message"]) == 1 else None
        orderbook = paths["orderbook"][0] if len(paths["orderbook"]) == 1 else None
        source_identity = {
            (path.relative_to(raw_root).as_posix(), path.stat().st_size)
            for path in (message, orderbook)
            if path is not None
        }
        matching_dataset = next(
            (
                manifest.dataset_id
                for manifest in imported.values()
                if (
                    manifest.symbol,
                    manifest.trade_date,
                    manifest.start_time_ms,
                    manifest.end_time_ms,
                    manifest.depth,
                )
                == (symbol, trade_date, start, end, depth)
                and {(item.name, item.size_bytes) for item in manifest.source_files} == source_identity
            ),
            None,
        )
        status = "invalid" if errors else "imported" if matching_dataset else "ready"
        candidates.append(
            LobsterCandidate(
                candidate_id=candidate_id,
                symbol=symbol,
                trade_date=trade_date,
                start_time_ms=start,
                end_time_ms=end,
                start_time=format_milliseconds(start),
                end_time=format_milliseconds(end),
                depth=depth,
                message_file=message.relative_to(raw_root).as_posix() if message else None,
                orderbook_file=orderbook.relative_to(raw_root).as_posix() if orderbook else None,
                message_file_size=message.stat().st_size if message else None,
                orderbook_file_size=orderbook.stat().st_size if orderbook else None,
                status=status,
                errors=errors,
                dataset_id=matching_dataset,
            )
        )
    return candidates


def validate_pair(
    candidate: LobsterCandidate,
    raw_dir: Path,
    *,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
) -> ValidationReport:
    if candidate.status == "invalid" or not candidate.message_file or not candidate.orderbook_file:
        return ValidationReport(valid=False, errors=candidate.errors or ["incomplete file pair"])
    message_path = safe_child(raw_dir, candidate.message_file)
    orderbook_path = safe_child(raw_dir, candidate.orderbook_file)
    errors: list[str] = []
    warnings: list[str] = []
    counts: Counter[str] = Counter()
    previous_timestamp = -1
    selected_last_timestamp = -1
    row_count = 0
    source_row_count = 0
    price_transition_checks = 0
    tracked_lifecycle_events = 0
    untracked_lifecycle_events = 0
    previous_book: dict[str, dict[int, int]] | None = None
    active_orders: dict[int, tuple[str, int, int]] = {}
    effective_start = candidate.start_time_ms if start_time_ms is None else start_time_ms
    effective_end = candidate.end_time_ms if end_time_ms is None else end_time_ms
    start_ns = effective_start * 1_000_000
    end_ns = effective_end * 1_000_000
    source_start_ns = candidate.start_time_ms * 1_000_000
    source_end_ns = candidate.end_time_ms * 1_000_000
    with message_path.open(newline="", encoding="utf-8") as messages, orderbook_path.open(
        newline="", encoding="utf-8"
    ) as books:
        for line_number, pair in enumerate(zip_longest(csv.reader(messages), csv.reader(books)), start=1):
            message_row, book_row = pair
            if message_row is None or book_row is None:
                errors.append("message and orderbook row counts differ")
                break
            try:
                event = parse_message(message_row, line_number=line_number)
            except ValueError as exc:
                errors.append(str(exc))
                if len(errors) >= 100:
                    errors.append("validation stopped after 100 errors")
                    break
                continue
            source_row_count += 1
            if event.timestamp_ns_since_midnight < previous_timestamp:
                errors.append(f"message line {line_number}: timestamp decreased")
            previous_timestamp = event.timestamp_ns_since_midnight
            try:
                asks, bids = _parse_book(book_row, depth=candidate.depth, line_number=line_number)
            except ValueError as exc:
                errors.append(str(exc))
                if len(errors) >= 100:
                    errors.append("validation stopped after 100 errors")
                    break
                continue
            ask_prices = [level["price_x10000"] for level in asks]
            bid_prices = [level["price_x10000"] for level in bids]
            if ask_prices != sorted(ask_prices) or len(ask_prices) != len(set(ask_prices)):
                errors.append(f"orderbook line {line_number}: ask levels are not ascending")
            if bid_prices != sorted(bid_prices, reverse=True) or len(bid_prices) != len(set(bid_prices)):
                errors.append(f"orderbook line {line_number}: bid levels are not descending")
            if ask_prices and bid_prices and bid_prices[0] > ask_prices[0]:
                errors.append(f"orderbook line {line_number}: book is crossed")
            elif ask_prices and bid_prices and bid_prices[0] == ask_prices[0]:
                warning = "dataset contains a locked order book"
                if warning not in warnings:
                    warnings.append(warning)
            if not source_start_ns <= event.timestamp_ns_since_midnight < source_end_ns:
                errors.append(f"message line {line_number}: timestamp is outside the filename session window")
            current_book = {
                "SELL": {level["price_x10000"]: level["quantity"] for level in asks},
                "BUY": {level["price_x10000"]: level["quantity"] for level in bids},
            }
            transition_checked, lifecycle_tracked = _validate_event_against_books(
                event,
                previous_book=previous_book,
                current_book=current_book,
                active_orders=active_orders,
                line_number=line_number,
                errors=errors,
            )
            price_transition_checks += int(transition_checked)
            tracked_lifecycle_events += int(lifecycle_tracked)
            if event.source_event_code in {2, 3, 4} and event.source_order_id not in active_orders and not lifecycle_tracked:
                untracked_lifecycle_events += 1
            previous_book = current_book
            if event.timestamp_ns_since_midnight < start_ns or event.timestamp_ns_since_midnight >= end_ns:
                continue
            selected_last_timestamp = event.timestamp_ns_since_midnight
            counts[event.event_kind] += 1
            row_count += 1
    if row_count == 0:
        errors.append("selected time window contains no events")
    if selected_last_timestamp >= 0 and selected_last_timestamp // 1_000_000 >= effective_end:
        errors.append("selected event is outside the requested time window")
    return ValidationReport(
        valid=not errors,
        row_count=row_count,
        event_counts=dict(sorted(counts.items())),
        checks={
            "message_orderbook_synchronization": not any(
                "row counts differ" in error for error in errors
            ),
            "sequence_and_timestamp_integrity": not any(
                "timestamp decreased" in error for error in errors
            ),
            "trading_session_boundaries": not any(
                "filename session window" in error for error in errors
            ),
            "valid_uncrossed_books": not any(
                "book is crossed" in error or "levels are not" in error for error in errors
            ),
            "price_level_consistency": not any(
                "visible quantity delta" in error for error in errors
            ),
            "order_lifecycle_consistency": not any(
                "source order" in error for error in errors
            ),
        },
        statistics={
            "source_row_count": source_row_count,
            "price_transition_checks": price_transition_checks,
            "tracked_lifecycle_events": tracked_lifecycle_events,
            "untracked_lifecycle_events": untracked_lifecycle_events,
            "active_tracked_orders_at_end": len(active_orders),
        },
        errors=errors,
        warnings=warnings,
    )


def convert_pair(
    candidate: LobsterCandidate,
    raw_dir: Path,
    destination: Path,
    *,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
) -> DatasetManifest:
    import pyarrow as pa
    import pyarrow.parquet as pq

    effective_start = candidate.start_time_ms if start_time_ms is None else start_time_ms
    effective_end = candidate.end_time_ms if end_time_ms is None else end_time_ms
    if effective_start < candidate.start_time_ms or effective_end > candidate.end_time_ms:
        raise ValueError("selected time window must be inside the source dataset range")
    report = validate_pair(
        candidate,
        raw_dir,
        start_time_ms=effective_start,
        end_time_ms=effective_end,
    )
    if not report.valid:
        raise ValueError("; ".join(report.errors))
    message_path = safe_child(raw_dir, candidate.message_file or "")
    orderbook_path = safe_child(raw_dir, candidate.orderbook_file or "")
    source_files = [
        _file_metadata(message_path, name=message_path.relative_to(raw_dir.resolve()).as_posix()),
        _file_metadata(orderbook_path, name=orderbook_path.relative_to(raw_dir.resolve()).as_posix()),
    ]
    digest = hashlib.sha256("".join(item.sha256 for item in source_files).encode()).hexdigest()[:12]
    dataset_id = (
        f"lobster-{candidate.symbol.lower()}-{candidate.trade_date}-"
        f"{effective_start}-{effective_end}-d{candidate.depth}-{digest}"
    )
    final_dir = destination.resolve() / dataset_id
    if (final_dir / "manifest.json").exists():
        return DatasetManifest.model_validate_json((final_dir / "manifest.json").read_text(encoding="utf-8"))
    destination.resolve().mkdir(parents=True, exist_ok=True)
    temporary = destination.resolve() / f".{dataset_id}.tmp-{uuid4().hex}"
    temporary.mkdir()
    try:
        event_writer: pq.ParquetWriter | None = None
        book_writer: pq.ParquetWriter | None = None
        event_rows: list[dict[str, object]] = []
        book_rows: list[dict[str, object]] = []
        with message_path.open(newline="", encoding="utf-8") as messages, orderbook_path.open(
            newline="", encoding="utf-8"
        ) as books:
            for sequence, (message_row, book_row) in enumerate(
                zip(csv.reader(messages), csv.reader(books), strict=True),
                start=1,
            ):
                event = parse_message(message_row, line_number=sequence)
                if event.timestamp_ns_since_midnight < effective_start * 1_000_000:
                    continue
                if event.timestamp_ns_since_midnight >= effective_end * 1_000_000:
                    break
                event_rows.append(event.as_dict(sequence=sequence, symbol=candidate.symbol, trade_date=candidate.trade_date))
                asks, bids = _parse_book(book_row, depth=candidate.depth, line_number=sequence)
                book_rows.append(
                    {
                        "source_sequence": sequence,
                        "timestamp_ns_since_midnight": event.timestamp_ns_since_midnight,
                        "depth": candidate.depth,
                        "asks": asks,
                        "bids": bids,
                    }
                )
                if len(event_rows) >= 50_000:
                    event_writer, book_writer = _write_chunks(
                        pa, pq, temporary, event_rows, book_rows, event_writer, book_writer
                    )
                    event_rows.clear()
                    book_rows.clear()
        if event_rows:
            event_writer, book_writer = _write_chunks(
                pa, pq, temporary, event_rows, book_rows, event_writer, book_writer
            )
        if event_writer is None or book_writer is None:
            raise ValueError("dataset is empty")
        event_writer.close()
        book_writer.close()
        outputs = [
            _file_metadata(temporary / "events.parquet"),
            _file_metadata(temporary / "book_snapshots.parquet"),
        ]
        manifest = DatasetManifest(
            dataset_id=dataset_id,
            symbol=candidate.symbol,
            trade_date=candidate.trade_date,
            start_time_ms=effective_start,
            end_time_ms=effective_end,
            depth=candidate.depth,
            row_count=report.row_count,
            event_counts=report.event_counts,
            imported_at=datetime.now(timezone.utc),
            source_files=source_files,
            output_files=outputs,
            warnings=report.warnings,
        )
        (temporary / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        temporary.rename(final_dir)
        return manifest
    except Exception:
        _remove_temporary_tree(temporary)
        raise


def iter_manifests(processed_dir: Path) -> Iterator[tuple[DatasetManifest, Path]]:
    root = processed_dir.resolve()
    if not root.exists():
        return
    for path in sorted(root.glob("*/manifest.json")):
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or resolved.parent.parent != root:
            continue
        try:
            manifest = DatasetManifest.model_validate_json(resolved.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.status == "ready":
            yield manifest, resolved.parent


def candidate_identifier(key: tuple[object, ...]) -> str:
    raw = "|".join(str(value) for value in key)
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def safe_child(root: Path, name: str) -> Path:
    path = (root.resolve() / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("dataset file must be a regular file under the configured raw directory")
    return path


def _parse_book(row: list[str], *, depth: int, line_number: int) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    if len(row) != depth * 4:
        raise ValueError(f"orderbook line {line_number}: expected {depth * 4} columns, found {len(row)}")
    asks: list[dict[str, int]] = []
    bids: list[dict[str, int]] = []
    try:
        values = [int(value) for value in row]
    except ValueError as exc:
        raise ValueError(f"orderbook line {line_number}: invalid integer") from exc
    for index in range(depth):
        ask_price, ask_size, bid_price, bid_size = values[index * 4 : index * 4 + 4]
        if ask_size < 0 or bid_size < 0:
            raise ValueError(f"orderbook line {line_number}: size must be non-negative")
        if ask_size > 0 and ask_price != DUMMY_ASK_PRICE:
            if ask_price <= 0:
                raise ValueError(f"orderbook line {line_number}: occupied ask price must be positive")
            asks.append({"level": index + 1, "price_x10000": ask_price, "quantity": ask_size})
        if bid_size > 0 and bid_price != DUMMY_BID_PRICE:
            if bid_price <= 0:
                raise ValueError(f"orderbook line {line_number}: occupied bid price must be positive")
            bids.append({"level": index + 1, "price_x10000": bid_price, "quantity": bid_size})
    return asks, bids


def _validate_event_against_books(
    event: ParsedMessage,
    *,
    previous_book: dict[str, dict[int, int]] | None,
    current_book: dict[str, dict[int, int]],
    active_orders: dict[int, tuple[str, int, int]],
    line_number: int,
    errors: list[str],
) -> tuple[bool, bool]:
    transition_checked = False
    lifecycle_tracked = False
    visible_delta = {1: 1, 2: -1, 3: -1, 4: -1}.get(event.source_event_code)
    if (
        visible_delta is not None
        and previous_book is not None
        and event.book_side is not None
        and (
            event.price_x10000 in previous_book[event.book_side]
            and (
                event.price_x10000 in current_book[event.book_side]
                or visible_delta < 0
            )
        )
    ):
        observed = current_book[event.book_side].get(event.price_x10000, 0) - previous_book[
            event.book_side
        ].get(event.price_x10000, 0)
        expected = visible_delta * event.size
        transition_checked = True
        if observed != expected:
            errors.append(
                f"orderbook line {line_number}: visible quantity delta {observed} "
                f"does not match message delta {expected}"
            )
    if event.source_event_code in {5, 6, 7} and previous_book is not None and current_book != previous_book:
        errors.append(
            f"orderbook line {line_number}: {event.event_kind.lower()} unexpectedly changed visible depth"
        )

    if event.source_event_code == 1:
        if event.source_order_id in active_orders:
            errors.append(f"message line {line_number}: duplicate active source order id")
        elif event.book_side is not None:
            active_orders[event.source_order_id] = (
                event.book_side,
                event.price_x10000,
                event.size,
            )
            lifecycle_tracked = True
        if current_book.get(event.book_side or "", {}).get(event.price_x10000, 0) < event.size:
            errors.append(f"orderbook line {line_number}: added source order is absent from visible depth")
    elif event.source_event_code in {2, 3, 4}:
        existing = active_orders.get(event.source_order_id)
        if existing is not None:
            lifecycle_tracked = True
            side, price, remaining = existing
            if side != event.book_side or price != event.price_x10000:
                errors.append(f"message line {line_number}: source order side or price changed")
            if event.size > remaining:
                errors.append(f"message line {line_number}: source order volume is over-consumed")
            elif event.source_event_code == 3 and event.size != remaining:
                errors.append(f"message line {line_number}: delete does not remove the remaining source order volume")
            else:
                new_remaining = remaining - event.size
                if event.source_event_code == 3 or new_remaining == 0:
                    active_orders.pop(event.source_order_id, None)
                else:
                    active_orders[event.source_order_id] = (side, price, new_remaining)
    return transition_checked, lifecycle_tracked


def _write_chunks(pa, pq, directory, event_rows, book_rows, event_writer, book_writer):
    event_table = pa.Table.from_pylist(event_rows, schema=_event_schema(pa))
    book_table = pa.Table.from_pylist(book_rows, schema=_book_schema(pa))
    if event_writer is None:
        event_writer = pq.ParquetWriter(directory / "events.parquet", event_table.schema, compression="zstd")
        book_writer = pq.ParquetWriter(directory / "book_snapshots.parquet", book_table.schema, compression="zstd")
    event_writer.write_table(event_table)
    book_writer.write_table(book_table)
    return event_writer, book_writer


def _event_schema(pa):
    return pa.schema(
        [
            ("source_sequence", pa.int64()),
            ("timestamp_ns_since_midnight", pa.int64()),
            ("event_kind", pa.string()),
            ("source_event_code", pa.int8()),
            ("source_order_id", pa.int64()),
            ("size", pa.int64()),
            ("price_x10000", pa.int64()),
            ("direction", pa.int8()),
            ("book_side", pa.string()),
            ("aggressor_side", pa.string()),
            ("halt_state", pa.string()),
            ("symbol", pa.string()),
            ("trade_date", pa.string()),
        ]
    )


def _book_schema(pa):
    level = pa.struct(
        [
            ("level", pa.int16()),
            ("price_x10000", pa.int64()),
            ("quantity", pa.int64()),
        ]
    )
    return pa.schema(
        [
            ("source_sequence", pa.int64()),
            ("timestamp_ns_since_midnight", pa.int64()),
            ("depth", pa.int16()),
            ("asks", pa.list_(level)),
            ("bids", pa.list_(level)),
        ]
    )


def _file_metadata(path: Path, *, name: str | None = None) -> DatasetFile:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return DatasetFile(name=name or path.name, size_bytes=path.stat().st_size, sha256=digest.hexdigest())


def _remove_temporary_tree(path: Path) -> None:
    if not path.exists() or not path.name.startswith(".lobster-") or ".tmp-" not in path.name:
        return
    for child in path.iterdir():
        if child.is_file():
            child.unlink()
    path.rmdir()
