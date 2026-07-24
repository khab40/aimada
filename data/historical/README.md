# Canonical historical CSV v1

Each runnable dataset is a directory containing `manifest.json` and `events.csv`.
The Java control plane validates the checksum, row count, timestamp order, source
sequence, and complete order lifecycle before replay.

The CSV header is fixed:

```text
source_sequence,timestamp_ns,event_type,order_id,participant_id,side,price_ticks,quantity_lots
```

- `source_sequence`: strictly increasing positive source-feed sequence.
- `timestamp_ns`: non-decreasing nanoseconds since midnight.
- `event_type`: `ADD`, `MODIFY`, `CANCEL`, or `MARKET`.
- `order_id`, `participant_id`: `[A-Za-z0-9._-]+`; replay namespaces both before
  they enter the canonical exchange.
- `side`: `BUY` or `SELL`.
- `price_ticks`: positive integer ticks for `ADD`; optional for `MODIFY`; empty
  for `CANCEL` and `MARKET`.
- `quantity_lots`: positive integer lots except `CANCEL`, which uses `0`.

The adapter is intentionally strict and does not infer labels. A historical-only
run has no attack ground truth. Hybrid labels are emitted only by a manually
launched synthetic scenario.

For paired LOBSTER message/order-book data, use the existing ingestion path
documented in [data/lobster](../lobster/README.md). Both formats share the Java
hybrid replay guarantees in
[ARD-0023](../../docs/architecture/ARD-0023-hybrid-historical-replay.md).
