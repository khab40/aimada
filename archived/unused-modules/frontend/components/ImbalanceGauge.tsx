export function ImbalanceGauge({ value = 0 }: { value?: number }) {
  return (
    <section>
      <h2>Imbalance</h2>
      <progress value={Math.abs(value)} max={1} />
    </section>
  );
}
