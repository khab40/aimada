import type { BenchmarkResult } from "@/types/arena";

export function BenchmarkTable({ rows = [] }: { rows?: BenchmarkResult[] }) {
  return (
    <section className="benchmark-table-panel">
      <h2>Benchmark</h2>
      <table className="benchmark-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Precision</th>
            <th>Recall</th>
            <th>F1</th>
            <th>Avg latency</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.scenario}>
              <td>{row.scenario}</td>
              <td>{row.precision.toFixed(2)}</td>
              <td>{row.recall.toFixed(2)}</td>
              <td>{row.f1.toFixed(2)}</td>
              <td>{row.avg_detection_latency_ms ? `${row.avg_detection_latency_ms} ms` : "n/a"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
