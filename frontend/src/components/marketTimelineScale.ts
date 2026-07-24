const compactPriceFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2
});

const largePriceFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0
});

const microValueFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2
});

export function getTimelinePriceDomain(prices: number[]): [number, number] {
  const finitePrices = prices.filter(Number.isFinite);
  if (!finitePrices.length) {
    return [0, 1];
  }

  const minimum = Math.min(...finitePrices);
  const maximum = Math.max(...finitePrices);
  const range = maximum - minimum;
  const referencePrice = Math.max(Math.abs(minimum), Math.abs(maximum), 1);
  const padding = range > 0
    ? Math.max(range * 0.12, referencePrice * 0.0001)
    : Math.max(referencePrice * 0.001, 0.01);

  return [minimum - padding, maximum + padding];
}

export function getTimelineSpreadDomain(spreads: number[]): [number, number] {
  const maximum = Math.max(0, ...spreads.filter(Number.isFinite));
  const paddedMaximum = Number((maximum * 1.12).toPrecision(12));
  return [0, maximum > 0 ? paddedMaximum : 1];
}

export function formatTimelinePrice(price: number) {
  if (!Number.isFinite(price)) {
    return "—";
  }
  return Math.abs(price) >= 10_000
    ? largePriceFormatter.format(price)
    : compactPriceFormatter.format(price);
}

export function formatTimelineMicroValue(value: number) {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return microValueFormatter.format(value);
}
