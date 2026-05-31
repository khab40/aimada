import type { OrderBookSnapshot } from "../types/arena";

export function OrderBookLadder({ snapshot }: { snapshot?: OrderBookSnapshot }) {
  return (
    <section>
      <h2>Order Book</h2>
      <pre>{JSON.stringify(snapshot ?? { bids: [], asks: [] }, null, 2)}</pre>
    </section>
  );
}
