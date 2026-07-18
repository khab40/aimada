# Kernel Authority Rollout

The Python control plane now owns one explicit authority router for versioned Protobuf kernel requests. The router is used by `POST /api/kernel/run`; its result headers identify the authority and rollout decision.

Python remains the default:

```text
KERNEL_AUTHORITY_MODE=python
JAVA_KERNEL_ROLLOUT_PERCENTAGE=0
JAVA_KERNEL_PYTHON_REPLAY_PERCENTAGE=100
JAVA_KERNEL_FALLBACK_TO_PYTHON=true
```

## Modes

- `python`: invoke only the Python reference. Merely configuring a Java target cannot call Java.
- `shadow`: return Python and mirror the identical request to bounded background Java comparison.
- `java`: assign a deterministic percentage of run ids to Java; unselected requests remain Python holdbacks.

Rollout and replay cohort selection use separate SHA-256-derived buckets of `run_id`, so the same run remains in the same cohort across processes and restarts.

## Java Rollout Safety

For a Java-selected request:

1. Call Java with the configured gRPC deadline.
2. If selected for Python replay, run the reference and compare the complete deterministic result.
3. Publish Java only if the call succeeded and sampled parity matched.
4. With fallback enabled, publish Python on Java transport failure or known parity mismatch.
5. With fallback disabled, return a service error instead of silently publishing a failed or known-divergent Java result.

Decisions are persisted to `outputs/kernel/authority-decisions.jsonl`; shadow outcomes use `outputs/kernel/shadow-outcomes.jsonl`. Result headers are:

- `X-Kernel-Authority: python|java`;
- `X-Kernel-Decision: python|shadow_python|holdback_python|java|fallback_error|fallback_mismatch`.

## Rollout Sequence

Use the following sequence after deploying a reachable Java control plane:

1. `python`, Java rollout `0`.
2. `shadow`, wait for zero unexplained mismatch/error/skip outcomes.
3. `java`, rollout `1`, Python replay `100`, fallback `true`.
4. Increase Java rollout through `5`, `25`, `50`, and `100` only after the observation window passes.
5. Keep Python replay at `100` initially; reduce it only after sustained parity and with a documented minimum sample.

Rollback is one configuration change: set `KERNEL_AUTHORITY_MODE=python` and restart the Python control plane. Rollout percentages are ignored in Python mode.

## API

`POST /api/kernel/run` accepts and returns `application/x-protobuf` using `SimulationRequest` and `SimulationResult`. Requests above 8 MiB are rejected. Invalid wire data or deterministic inputs return HTTP 400; a fail-closed Java authority error returns HTTP 503.

`GET /api/kernel/status` exposes mode, rollout/replay percentages, fallback policy, and shadow queue metrics without exposing the Java target or run ids.

This step makes Java authority available and controllable but does not make it the default. Step 17 owns the final default change and permanent Python replay policy.
