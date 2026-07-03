import type { OrderBookSnapshot, PriceLevel } from "@/types/arena";

export function OrderBookLadder({ snapshot }: { snapshot: OrderBookSnapshot }) {
  const hasLevels = snapshot.asks.length > 0 || snapshot.bids.length > 0;
  const maxQuantity = Math.max(
    1,
    ...snapshot.asks.map((level) => level.quantity),
    ...snapshot.bids.map((level) => level.quantity)
  );
  const asksDescending = [...snapshot.asks].sort((left, right) => right.price - left.price);
  const bidsDescending = [...snapshot.bids].sort((left, right) => right.price - left.price);

  return (
    <section className="order-book-ladder">
      <div className="ladder-header">
        <h2>Order Book</h2>
        <span>Best {formatPrice(snapshot.best_bid)} / {formatPrice(snapshot.best_ask)}</span>
      </div>
      {!hasLevels ? (
        <div className="empty-state">Waiting for order-book levels.</div>
      ) : null}
      <div className="ladder-columns">
        <div className="ladder-side">
          <h3>Asks</h3>
          {asksDescending.map((level) => (
            <BookLevelRow
              key={`ask-${level.price}`}
              level={level}
              maxQuantity={maxQuantity}
              side="ask"
            />
          ))}
        </div>
        <div className="midline">
          <span>Mid</span>
          <strong>{formatPrice(snapshot.mid)}</strong>
          <span>Spread {formatPrice(snapshot.spread)}</span>
        </div>
        <div className="ladder-side">
          <h3>Bids</h3>
          {bidsDescending.map((level) => (
            <BookLevelRow
              key={`bid-${level.price}`}
              level={level}
              maxQuantity={maxQuantity}
              side="bid"
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function BookLevelRow({
  level,
  maxQuantity,
  side
}: {
  level: PriceLevel;
  maxQuantity: number;
  side: "ask" | "bid";
}) {
  const barWidth = `${Math.max(4, Math.min(100, (level.quantity / maxQuantity) * 100))}%`;
  const isAbuser = level.owner === "abuser" || level.agent_id?.toLowerCase().includes("abuser");

  return (
    <div className={`book-level ${side} ${isAbuser ? "abuser-owned" : ""}`}>
      <div className="book-level-bar" style={{ width: barWidth }} />
      <span className="book-price">{formatPrice(level.price)}</span>
      <strong className="book-size">{level.quantity.toFixed(3)}</strong>
      {isAbuser ? <em>suspect</em> : null}
    </div>
  );
}

function formatPrice(value: number | null) {
  return value === null ? "n/a" : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}
