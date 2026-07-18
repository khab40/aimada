# Differential Parity Harness

`DifferentialParityHarness` is the control-plane comparison boundary between the authoritative Python kernel and a candidate runner such as the generated Java gRPC client method.

The harness serializes the input request once with deterministic Protobuf encoding and reconstructs independent request objects for each runner. A runner therefore cannot alter the request observed by the other implementation.

## Compared Outputs

The report compares and classifies:

- contract version and run identity;
- ordered canonical events and the first divergent sequence;
- event-stream hashes;
- executions extracted from the event stream;
- every LOB snapshot and the final L2 book;
- final-book hashes;
- all ordered quantized market and detector metrics;
- termination reason and optional detail.

Reports contain counts, a stable ordered set of mismatch categories, concise mismatch details, and a JSON-compatible `to_dict()` representation. Complete Protobuf payloads remain available on the returned `DifferentialRun` but are not duplicated into the summary.

## Runner Contract

A runner is any callable from `SimulationRequest` to `SimulationResult`. The Python reference method and generated gRPC blocking method both satisfy this shape:

```python
harness = DifferentialParityHarness(PythonReferenceKernel().run, java_stub.RunSimulation)
run = harness.run(request)
```

Transport failures and authority/fallback behavior are intentionally outside this comparator. Shadow mode will own those policies while reusing this exact report.

## Verification

Tests compare all six immutable golden corpus cases and inject targeted divergences into executions, snapshots, final book state, hashes, metrics, termination, identity, and event length. Each mutation must be attributed to the expected category and event sequence.
