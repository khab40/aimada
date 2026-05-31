export function BenchmarkTable({ rows = [] }: { rows?: Array<Record<string, unknown>> }) {
  return (
    <section>
      <h2>Benchmark</h2>
      <pre>{JSON.stringify(rows, null, 2)}</pre>
    </section>
  );
}
