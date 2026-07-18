# gRPC Kernel Boundary

The versioned `lob.exchange.v1.SimulationKernel` service is the process boundary shared by the Python reference kernel and Java candidate kernel. It exposes one unary operation:

```protobuf
rpc RunSimulation(SimulationRequest) returns (SimulationResult);
```

Both request and result use the deterministic Protobuf contract directly. No JSON conversion, floating-point value, Spring object, FastAPI model, persistence handle, or telemetry object enters the kernel call.

## Implementations

- `backend/app/contracts/grpc_reference.py` adapts the authoritative `PythonReferenceKernel` to the generated Python service interface.
- `java/kernel-grpc` adapts the framework-free `JavaSimulationKernel` to the generated Java service interface.
- `exchange-proto` owns Java message and gRPC stub generation; `scripts/generate_protos.py` owns checked-in Python message and gRPC bindings.

The adapters do not alter simulation behavior. Python remains authoritative; the Java service is a candidate endpoint for parity and later shadow execution.

## Failure Contract

- Invalid contract versions, malformed deterministic inputs, and unsupported scenario parameters return gRPC `INVALID_ARGUMENT`.
- Unexpected Java candidate failures return `INTERNAL` without changing the deterministic result schema.
- Transport deadlines, retries, authentication, and deployment policy belong outside the kernel and will be defined with shadow-mode integration.

## Verification

Python tests prove that the service delegates to the reference runner and maps contract errors. Java uses an in-process gRPC server and generated client to execute a checked-in request and compare the complete result with the exact golden Protobuf result. Generated Python binding freshness and the full Gradle build are required checks.

This step establishes a callable language boundary only. Differential reporting, live shadow routing, operational telemetry, and authority changes remain separate migration gates.
