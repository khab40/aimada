# Java Kernel Migration

LOB Arena will migrate its deterministic exchange kernel from Python to Java 25 through differential parity, not through a one-time backend rewrite. Python remains the reference implementation until Java produces the same ordered exchange stream, book checkpoints, trades, hashes, and metrics.

## Frozen Migration Boundary

The first Java authority boundary contains only deterministic hot-loop components:

| Component | Initial authority | Migration condition |
| --- | --- | --- |
| Canonical event contract | Protobuf shared by both languages | Python and Java round-trip the same versioned messages |
| Simulation clock and scheduler | Python reference | Java passes ordering and timing vectors |
| PRNG streams | Python reference | Bit-exact Java/Python vectors pass |
| Order book and matching | Python reference | Events, trades, remainders, priority, and snapshots match |
| Scenario execution | Python reference | Complete scenario event hashes match |
| Market features and deterministic detectors | Python | Move only after kernel parity; metrics must match |
| REST, WebSocket, persistence, and orchestration | Python/FastAPI | Remain Python during kernel migration |
| Frontend | React/TypeScript | No migration planned |
| Java control plane | None initially | Spring Boot is introduced after the plain Java kernel boundary is stable |

Spring objects, dependency injection, HTTP concerns, persistence clients, telemetry exporters, and message brokers must not enter the kernel hot loop.

## Authority Modes

- `python`: Python is authoritative and Java is not invoked.
- `shadow`: both kernels receive an identical Protobuf request; Python publishes results and Java produces a parity report only.
- `java`: Java publishes results, with sampled Python replay retained for rollback and regression detection.

The default cannot move from `python` to `shadow` or from `shadow` to `java` without the relevant parity, performance, observability, and rollback gates passing.

## Completion Gates

Java kernel authority requires all of the following:

1. The Protobuf schema is versioned and compatibility-tested.
2. Numeric units, event ordering, identifiers, PRNG streams, rounding, and hashes are language-neutral specifications.
3. Python is wrapped as a Protobuf reference runner without behavioral drift.
4. The golden corpus covers every exchange event and active scenario.
5. Java passes exact event, trade, snapshot, final-book, and hash parity.
6. Quantized detector inputs and metrics match the frozen tolerance policy.
7. Shadow mode reports no unexplained divergence for the agreed run/seed corpus.
8. Java meets the agreed latency, throughput, allocation, and resource limits.
9. Metrics, traces, health, parity failures, and rollback controls are operational.
10. Python reference replay remains in CI after Java becomes authoritative.

## Toolchain Policy

- Target Java version: 25.
- The repository owns a Gradle wrapper and Java toolchain declaration; developer-global Gradle is not required.
- Protobuf and gRPC generation is owned by the build; developer-global `protoc` is not required.
- CI verifies generated-source freshness and builds with the declared Java toolchain.
- A Java 21-only development machine can launch the repository wrapper, which auto-provisions the declared Java 25 compile/test toolchain; no global Gradle or `protoc` is required.

## Explicit Non-Goals During Parity

- No full FastAPI-to-Spring rewrite before kernel parity.
- No Kafka for an individual simulation's internal event queue.
- No Chronicle Queue without a measured durable-journal requirement.
- No Agrona adoption without profiling evidence.
- No ClickHouse or Parquet migration as part of kernel correctness work.
- No removal of the Python reference implementation during the stability period.

## Implementation Sequence

| Step | Status | Deliverable |
| --- | --- | --- |
| 1 | Done | Scope, authority boundary, gates, toolchain policy, and rollback rules |
| 2 | Done | `lob.exchange.v1` Protobuf messages, checked-in Python bindings, freshness validation, and round-trip tests |
| 3 | Done | Fixed-point units, total ordering, SplitMix64 streams, identifiers, rounding, semantics, and executable vectors |
| 4 | Done | Explicit canonical event/book bytes, SHA-256 digests, stream hash chain, and golden vectors |
| 5 | Done | Authoritative Python Protobuf runner with exact event/book conversion, hashes, and quantized metrics |
| 6 | Done | Immutable deterministic Protobuf parity corpus covering all scenarios, event types, empty-book optionals, checksums, and canonical hashes |
| 7 | Done | Repository-owned Gradle 9.6.1 wrapper, Java 25 toolchains, generated shared Protobuf module, framework-free kernel module, Spring Boot control plane, and CI |
| 8 | Done | Java total ordering, fixed-point/metric rules, SplitMix64 named streams, identifiers, canonical encodings, and SHA-256 event/book/stream hashes with exact golden parity |
| 9 | Done | Integer tick/lot order book, best-price/FIFO matching, modify/cancel rules, executions, owner aggregation, and deterministic Protobuf snapshots/events |
| 10 | Done | Java Protobuf simulation runner with logical clock, ordered normal agents, all active scenarios, baseline repair, per-tick snapshots, deterministic features/detectors, limits, and exact golden outputs |
| 11 | Done | Shared unary gRPC contract, generated Python/Java stubs, Python reference adapter, Java candidate adapter, error mapping, and exact in-process golden-result test |
| 12 | Planned | Differential parity harness |
| 13 | Planned | Offline and live shadow modes |
| 14 | Planned | Benchmarks and profiling gates |
| 15 | Planned | OpenTelemetry and Prometheus observability |
| 16 | Planned | Incremental Java authority rollout |
| 17 | Planned | Permanent Python reference replay policy |

## Related Documentation

- [ARD-0018: Canonical Exchange Event Stream](architecture/ARD-0018-canonical-exchange-event-stream.md)
- [ARD-0019: Python Reference And Java Kernel Migration](architecture/ARD-0019-python-reference-java-kernel-migration.md)
- [High-Level Architecture](architecture.md)
- [Runtime Model](runtime-model.md)
- [Determinism Contract V1](determinism-contract-v1.md)
- [Canonical Hashing V1](canonical-hashing-v1.md)
- [Golden Parity Corpus V1](golden-parity-corpus-v1.md)
- [Java Integer Order Book](java-order-book.md)
- [Java Simulation Kernel](java-simulation-kernel.md)
- [gRPC Kernel Boundary](grpc-kernel-boundary.md)
