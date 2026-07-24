import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  formatTimelineMicroValue,
  formatTimelinePrice,
  getTimelinePriceDomain,
  getTimelineSpreadDomain
} from "../src/components/marketTimelineScale.ts";

describe("market timeline scaling", () => {
  it("keeps cent-level historical movement visible", () => {
    const prices = [135.29, 135.31, 135.37];
    const [minimum, maximum] = getTimelinePriceDomain(prices);

    assert.ok(minimum < Math.min(...prices));
    assert.ok(maximum > Math.max(...prices));
    assert.ok(maximum - minimum < 0.2);
  });

  it("adds a proportional domain around a flat price", () => {
    const [minimum, maximum] = getTimelinePriceDomain([135.37, 135.37]);

    assert.ok(minimum < 135.37);
    assert.ok(maximum > 135.37);
    assert.ok(maximum - minimum < 0.5);
  });

  it("formats price ticks without clipping-prone precision noise", () => {
    assert.equal(formatTimelinePrice(120.00001), "120.00");
    assert.equal(formatTimelinePrice(135.685), "135.69");
    assert.equal(formatTimelinePrice(68_000), "68,000");
    assert.equal(formatTimelinePrice(Number.NaN), "—");
  });

  it("uses a non-negative independent spread domain", () => {
    assert.deepEqual(getTimelineSpreadDomain([0.75, 1.5]), [0, 1.68]);
    assert.deepEqual(getTimelineSpreadDomain([]), [0, 1]);
    assert.equal(formatTimelineMicroValue(1.50001), "1.5");
  });
});
