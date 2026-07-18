# Kernel Observability

Kernel observability is implemented around gRPC and shadow orchestration, not inside the deterministic hot loop. Metric and trace failures are isolated from kernel results.

## Java Control Plane

Spring Boot Actuator exposes health, diagnostic metrics, and Prometheus scrape endpoints. The candidate gRPC server remains disabled by default and can be started as a control-plane-managed boundary:

```bash
LOB_KERNEL_GRPC_ENABLED=true ./gradlew :control-plane:bootRun
```

Relevant endpoints are:

- `/actuator/health`;
- `/actuator/metrics`;
- `/actuator/prometheus`.

The gRPC instrumentation emits:

| Meter | Type | Labels |
| --- | --- | --- |
| `lob.kernel.grpc.requests` | counter | `outcome=completed|invalid_argument|internal_error` |
| `lob.kernel.grpc.duration` | histogram timer | bounded `outcome` |
| `lob.kernel.grpc.events` | distribution summary | none |

Run ids, scenario ids, symbols, event ids, and exception messages are deliberately excluded from labels. They belong in trace/log details, not time-series dimensions.

Each call also creates a `lob.kernel.grpc` Micrometer observation. Spring Boot bridges it to OpenTelemetry, adding bounded `contract.version` and `outcome` attributes. OTLP export is opt-in:

```bash
LOB_KERNEL_OTLP_ENABLED=true \
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://otel-collector:4318/v1/traces \
LOB_KERNEL_TRACE_SAMPLE_PROBABILITY=0.1 \
./gradlew :control-plane:bootRun
```

OTLP metric push is separately controlled by `LOB_KERNEL_OTLP_METRICS_ENABLED`; it is off by default because Prometheus scraping is the primary metric path. Local tests never require a collector.

## Python Shadow Metrics

Every `LiveShadowKernel` owns a thread-safe `ShadowMetrics` registry with:

- pending work and configured pending limit gauges;
- bounded `match`, `mismatch`, `error`, and `skipped` outcome counters;
- candidate-duration sum/count by the same bounded status.

`snapshot()` supports API/status integration, while `prometheus()` renders scrape-ready text. Run ids and error details never become labels. Step 16 will attach the selected authority router's registry to the existing FastAPI `/metrics` response.

## Prometheus and Grafana Templates

- `monitoring/prometheus/java-kernel.yml` scrapes the Java actuator and existing Python metric endpoints.
- `monitoring/grafana/dashboards/java-kernel.json` provides request rate, p95/p99 RPC latency, shadow pressure/outcomes, allocation rate, and canonical event-rate panels.

These are provisioning templates only; this step adds no Docker containers. Adjust scrape targets to the deployment service names.

Recommended alerts are:

- any sustained `mismatch` increase;
- any `error` increase after Java becomes a required candidate;
- `skipped` outcomes or pending/limit above 80%;
- p99 latency above the rollout SLO;
- absence of Java scrape data while shadow or Java mode is enabled.

Grafana is a visualization consumer, never a kernel dependency. Prometheus scraping and OTLP exporting remain outside simulation execution.
