const DEFAULT_PRICE_BUCKET = 5;
const MAX_PRICE_DECIMALS = 8;
const MIN_PRICE_GAP = 1e-9;

type PriceLevelLike = {
  price: number;
};

type OrderBookLike = {
  asks: PriceLevelLike[];
  bids: PriceLevelLike[];
  mid: number | null;
  spread: number | null;
};

type SnapshotLike = {
  book: OrderBookLike;
};

export function inferPriceBucket(snapshots: readonly SnapshotLike[]) {
  const book = snapshots.at(-1)?.book;
  if (!book) {
    return DEFAULT_PRICE_BUCKET;
  }

  const gaps = [
    ...priceGaps(book.asks),
    ...priceGaps(book.bids)
  ];
  if (gaps.length) {
    return normalizePriceStep(Math.min(...gaps));
  }

  const spread = book.spread;
  return spread !== null && spread !== undefined && Number.isFinite(spread) && spread > 0
    ? normalizePriceStep(spread)
    : DEFAULT_PRICE_BUCKET;
}

export function bucketHeatmapPrice(price: number, priceBucket: number) {
  if (!Number.isFinite(price) || !Number.isFinite(priceBucket) || priceBucket <= 0) {
    return price;
  }
  return Number((Math.round(price / priceBucket) * priceBucket).toFixed(priceDecimals(priceBucket)));
}

export function selectVisibleHeatmapPrices(
  snapshot: OrderBookLike | undefined,
  visibleLevels: number,
  priceBucket: number
) {
  if (!snapshot) {
    return [];
  }

  const midpoint = snapshot.mid;
  const levelCount = Math.max(0, Math.floor(visibleLevels));
  if (midpoint === null || midpoint === undefined || !Number.isFinite(midpoint) || levelCount === 0) {
    return [];
  }

  const prices = Array.from(new Set(
    [...snapshot.asks, ...snapshot.bids]
      .map((level) => bucketHeatmapPrice(level.price, priceBucket))
      .filter(Number.isFinite)
  ));
  return prices
    .sort((left, right) => (
      Math.abs(left - midpoint) - Math.abs(right - midpoint) || right - left
    ))
    .slice(0, levelCount)
    .sort((left, right) => right - left);
}

export function formatHeatmapPrice(price: number, priceBucket: number) {
  const decimals = priceDecimals(priceBucket);
  return price.toLocaleString("en-US", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals
  });
}

function priceGaps(levels: readonly PriceLevelLike[]) {
  const prices = Array.from(new Set(
    levels.map((level) => level.price).filter(Number.isFinite)
  )).sort((left, right) => left - right);
  return prices
    .slice(1)
    .map((price, index) => price - prices[index])
    .filter((gap) => gap > MIN_PRICE_GAP);
}

function normalizePriceStep(step: number) {
  return Number(step.toPrecision(8));
}

function priceDecimals(step: number) {
  if (!Number.isFinite(step) || step <= 0) {
    return 0;
  }
  const fixed = step.toFixed(MAX_PRICE_DECIMALS).replace(/0+$/, "");
  return fixed.includes(".") ? fixed.split(".")[1].length : 0;
}
