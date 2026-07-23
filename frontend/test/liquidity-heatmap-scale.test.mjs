import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  bucketHeatmapPrice,
  formatHeatmapPrice,
  inferPriceBucket,
  selectVisibleHeatmapPrices
} from "../src/components/liquidityHeatmapScale.ts";

function historicalBook() {
  const bids = Array.from({ length: 30 }, (_, index) => ({
    price: Number((135.29 - index * 0.01).toFixed(2))
  }));
  const asks = Array.from({ length: 30 }, (_, index) => ({
    price: Number((135.31 + index * 0.01).toFixed(2))
  }));
  return {
    asks,
    best_ask: 135.31,
    best_bid: 135.29,
    bids,
    mid: 135.30,
    spread: 0.02
  };
}

describe("liquidity heatmap price scaling", () => {
  it("preserves cent-level historical prices instead of collapsing them into one $5 row", () => {
    const book = historicalBook();
    const bucket = inferPriceBucket([{ book }]);
    const bucketedPrices = new Set(
      [...book.asks, ...book.bids].map((level) => bucketHeatmapPrice(level.price, bucket))
    );
    const visiblePrices = selectVisibleHeatmapPrices(book, 20, bucket);

    assert.equal(bucket, 0.01);
    assert.equal(bucketedPrices.size, 60);
    assert.equal(visiblePrices.length, 20);
    assert.ok(visiblePrices.includes(135.29));
    assert.ok(visiblePrices.includes(135.31));
    assert.ok(Math.max(...visiblePrices) - Math.min(...visiblePrices) < 0.25);
    assert.equal(formatHeatmapPrice(135.4, bucket), "135.40");
  });

  it("retains the existing $5 grid for synthetic books", () => {
    const book = {
      asks: Array.from({ length: 10 }, (_, index) => ({ price: 68_002 + index * 5 })),
      bids: Array.from({ length: 10 }, (_, index) => ({ price: 67_998 - index * 5 })),
      mid: 68_000,
      spread: 4
    };

    const bucket = inferPriceBucket([{ book }]);

    assert.equal(bucket, 5);
    assert.equal(bucketHeatmapPrice(68_002, bucket), 68_000);
    assert.equal(formatHeatmapPrice(68_000, bucket), "68,000");
  });

  it("uses the current book increment immediately after switching data sources", () => {
    const historical = historicalBook();
    const synthetic = {
      asks: Array.from({ length: 10 }, (_, index) => ({ price: 68_002 + index * 5 })),
      bids: Array.from({ length: 10 }, (_, index) => ({ price: 67_998 - index * 5 })),
      mid: 68_000,
      spread: 4
    };

    assert.equal(inferPriceBucket([{ book: historical }, { book: synthetic }]), 5);
  });
});
