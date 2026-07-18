# Kernel Shadow Mode

Shadow execution evaluates the Java candidate without changing simulation authority. The Python reference result is always the published result in both supported paths.

## Offline Replay

Start the plain Java 25 gRPC candidate on macOS or Linux:

```bash
cd java
./gradlew :kernel-grpc:run --args=50051
```

In another terminal, replay the immutable parity corpus:

```bash
uv run --project backend python scripts/run_kernel_shadow_corpus.py \
  --target 127.0.0.1:50051 \
  --output outputs/kernel-shadow/parity-v1.jsonl
```

The command exits successfully only when every case matches. Each JSONL row contains the case identity, status, event/execution/snapshot counts, first divergent sequence, and categorized parity details. Candidate timeouts and transport failures are recorded as errors.

## Live Mirroring

`LiveShadowKernel` runs Python synchronously, returns that authoritative result, and submits the identical serialized request plus immutable reference result to bounded background comparison. A slow or unavailable Java candidate cannot replace or delay the completed Python result.

The caller supplies a report sink. Sink failures are logged and cannot change the authoritative result. Outcomes are one of:

- `match`: every compared deterministic output matches;
- `mismatch`: the candidate returned a result with structured parity differences;
- `error`: the candidate call failed or timed out;
- `skipped`: the configured pending-work bound was reached.

The queue is bounded by `max_pending`, concurrency is bounded by `max_workers`, and `drain()`/`close()` provide explicit test and shutdown behavior. `GrpcKernelRunner` applies a per-request deadline and owns its channel lifecycle.

## Authority and Safety

- Python exceptions remain authoritative failures.
- Java exceptions, deadlines, and capacity pressure become shadow outcomes.
- Requests are cloned from one deterministic byte sequence before either implementation sees them.
- Full candidate results are retained for synchronous offline investigation; live sinks receive compact reports.
- This step does not add Java authority, automatic fallback, retries, or production rollout configuration.

The step 13 verification started the real Java server and replayed all six golden scenarios through the Python gRPC client. All 320 events, 10 executions, 51 snapshots, final books, hashes, and metrics matched.
