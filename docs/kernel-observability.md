# Kernel Observability

Kernel observability is implemented around the Java HTTP/gRPC control plane, not inside the deterministic hot loop. Metric and trace failures are isolated from kernel results.

## Java Control Plane

Spring Boot Actuator exposes health, diagnostic metrics, and Prometheus scrape endpoints. The gRPC server can be started as a control-plane-managed boundary:

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

Trace export uses Spring Boot's `management.tracing.export.otlp.enabled` gate and defaults to disabled. OTLP metric push is separately controlled by `LOB_KERNEL_OTLP_METRICS_ENABLED`; it is off by default because Prometheus scraping is the primary metric path. Local tests and control-plane startup never require a collector.

The retired Python shadow/authority metrics are intentionally absent. Compatibility drift is a CI failure from exact golden-corpus replay, while production Java health, request outcomes, latency, and event counts remain available through Actuator and Prometheus.

## Prometheus and Grafana Templates

- `monitoring/prometheus/java-kernel.yml` scrapes the Java actuator and existing Python metric endpoints.
- `monitoring/grafana/dashboards/java-kernel.json` provides Java request rate, p95/p99 RPC latency, allocation rate, and canonical event-rate panels. Historical shadow panels may be removed from deployed dashboards.

These are provisioning templates only; this step adds no Docker containers. Adjust scrape targets to the deployment service names.

Recommended alerts are:

- Java error-rate increases;
- failed golden-corpus replay in CI;
- p99 latency above the rollout SLO;
- absence of Java scrape data while the kernel service is deployed.

Grafana is a visualization consumer, never a kernel dependency. Prometheus scraping and OTLP exporting remain outside simulation execution.
