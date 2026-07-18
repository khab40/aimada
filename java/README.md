# Java Candidate Kernel

This Gradle build contains the Java 25 candidate implementation. Python remains authoritative until the parity and rollout gates in [ARD-0019](../docs/architecture/ARD-0019-python-reference-java-kernel-migration.md) pass.

Modules:

- `exchange-proto` generates Java types directly from `contracts/proto` and reads the shared golden corpus in tests;
- `simulation-kernel` is the framework-free deterministic hot-loop boundary;
- `control-plane` is the separate Spring Boot API boundary and may depend on the kernel, never the reverse.

The kernel currently includes the frozen Java 25 implementations of event ordering, fixed-point conversion, half-even metric quantization, SplitMix64 and named streams, simulation identifiers, canonical event/book bytes, SHA-256 digests, and the rolling event-stream hash.

It also includes the integer-tick/lot order book and matching engine described in [Java Integer Order Book](../docs/java-order-book.md).

The complete candidate tick runner, normal agents, scenarios, baseline phase, and metric calculation are described in [Java Simulation Kernel](../docs/java-simulation-kernel.md).

On macOS or Linux, run:

```bash
./gradlew clean check
```

The checksum-pinned wrapper owns Gradle 9.6.1. The Foojay resolver auto-provisions a Java 25 toolchain when one is not installed, so a developer-global Gradle or Java 25 installation is not required. Generated Protobuf Java sources stay under `build/` and are not committed.
