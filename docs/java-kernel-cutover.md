# Java Kernel Default Cutover

The versioned `SimulationRequest`/`SimulationResult` kernel API now selects Java by default:

- authority mode: `java`;
- Java rollout: 100%;
- synchronous Python replay sample: 10%;
- Python fallback on Java error or known mismatch: enabled;
- permanent CI corpus replay: 100%.

The cutover applies to `POST /api/kernel/run`. FastAPI still owns REST/WebSocket orchestration, persistence, Nebius integration, and the interactive continuous simulation control plane. The React frontend remains unchanged. This is the component boundary frozen in ARD-0019, not a claim that the full backend moved to Java.

## Deployment

Compose now runs four purposeful services: Java kernel, Python backend, agent runner, and frontend. The Java service is a multi-stage, non-root Java 25 image:

- allow-listed build context contains the Java main sources and Protobuf schema only;
- tests, benchmark sources, docs, Git data, outputs, credentials, and Windows scripts stay outside the image context;
- build JDK and Gradle are absent from the runtime image;
- runtime user is `lobarena`;
- only the Spring Boot JAR and Java 25 JRE remain;
- local verified image size is approximately 149.6 MB.

The Java service exposes HTTP/Actuator on host port 8081 and gRPC on 50051. The backend waits for Java health before starting and connects over the Compose network at `java-kernel:50051`.

## Permanent Reference Policy

Python is not removed. The following are permanent release gates:

1. Python golden corpus generation and freshness tests remain.
2. Java exact golden tests remain.
3. The `cross-language-parity` CI job starts the real Spring/gRPC Java service and replays every corpus case from Python.
4. Runtime Python replay remains configurable and defaults to 10%.
5. A Java error or sampled mismatch falls back to Python and records the decision.
6. `KERNEL_AUTHORITY_MODE=python` is the immediate operational rollback.

An intentional deterministic behavior change still requires a new versioned contract/corpus decision; passing only one language's tests is insufficient.

## Verification Record

The final local cutover verification built the allow-listed image, started its health and gRPC endpoints, and sent the normal-market golden request through a default Java authority router with 100% verification replay. The response selected Java with no fallback and matched all 25 events, one execution, six snapshots, hashes, final book, and metrics.
