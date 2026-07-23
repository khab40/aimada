# ARD-0022: Historical Market Data Ingestion And Replay

Status: Accepted and Implemented

Date: 2026-07-23

## Context

LOB Arena needs a one-time administrative path for importing licensed local
LOBSTER files without turning the synthetic Arena into a vendor-specific data
pipeline. Historical replay must retain the Java control plane as the browser
WebSocket authority.

## Decision

- FastAPI owns file discovery, validation, Parquet conversion, manifests, and
  the dataset registry.
- Each batch import may cover the complete source pair or a bounded time
  window. The Data Ingestion UI exposes one-minute and five-minute presets;
  the selected start is inclusive and the computed end is exclusive.
- LOBSTER `price_x10000` remains an integer in the persisted contract.
- The Java control plane reads only normalized Parquet and manifest fields
  through `HistoricalMarketDataSource`.
- Synthetic and historical sources are mutually exclusive in this increment.
- The shared source boundary reserves `HybridMarketDataSource` for a future
  deterministic historical-baseline plus simulated-attack overlay.
- Streaming ingestion, distributed import jobs, and timestamp-paced replay are
  outside this increment.

## Storage Contract

Each ready dataset contains:

```text
data/processed/lobster/<dataset_id>/
├── events.parquet
├── book_snapshots.parquet
└── manifest.json
```

The manifest is written last and is the registry source of truth. Import occurs
in a temporary sibling directory followed by an atomic rename. A bounded
import records its effective start and end in the manifest and produces a
distinct dataset identifier, so multiple test slices may coexist.

## Consequences

LOBSTER parsing cannot leak into the simulator. Historical snapshots are never
mutated by synthetic orders. A future hybrid source must maintain a separate
overlay book and deterministic provenance rather than editing recorded state.
