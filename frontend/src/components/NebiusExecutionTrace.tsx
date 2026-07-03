export type NebiusExecutionTraceData = {
  artifactLink?: string | null;
  endpointId?: string | null;
  estimatedCost: string;
  executionType: "endpoint" | "job" | "streaming";
  fallback: "real" | "simulated";
  jobId?: string | null;
  lastExecutionTime: string;
  latency: string;
  model: string;
  runId: string;
  runtimeGpu: string;
  status: string;
  tokensIn: string;
  tokensOut: string;
};

export function NebiusExecutionTrace({
  trace,
  title = "Nebius Execution Trace"
}: {
  title?: string;
  trace: NebiusExecutionTraceData;
}) {
  return (
    <section className="nebius-execution-trace" aria-label={title}>
      <div className="section-heading-row">
        <h4>{title}</h4>
        <span className={`endpoint-badge ${trace.fallback === "simulated" ? "mock_fallback" : "healthy"}`}>
          {trace.fallback === "simulated" ? "simulated fallback" : "real"}
        </span>
      </div>
      <dl className="nebius-execution-grid">
        <TraceField label="Execution type" value={trace.executionType} />
        <TraceField label="Run id" value={trace.runId} />
        <TraceField label="Endpoint id" value={trace.endpointId ?? "-"} />
        <TraceField label="Job id" value={trace.jobId ?? "-"} />
        <TraceField label="Model" value={trace.model} />
        <TraceField label="Runtime/GPU" value={trace.runtimeGpu} />
        <TraceField label="Status" value={trace.status} />
        <TraceField label="Latency" value={trace.latency} />
        <TraceField label="Tokens in" value={trace.tokensIn} />
        <TraceField label="Tokens out" value={trace.tokensOut} />
        <TraceField label="Estimated cost" value={trace.estimatedCost} />
        <TraceField label="Artifact link" value={trace.artifactLink ?? "-"} />
        <TraceField label="Last execution time" value={trace.lastExecutionTime} />
      </dl>
    </section>
  );
}

export function AiCostLatencyCard({ trace }: { trace: NebiusExecutionTraceData }) {
  return (
    <NebiusExecutionTrace title="AI Cost & Latency" trace={trace} />
  );
}

function TraceField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
