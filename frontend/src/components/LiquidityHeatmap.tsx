import { useEffect, useMemo, useRef, useState } from "react";
import type { OrderBookSnapshot, PriceLevel } from "@/types/arena";

export type HeatmapFrame = {
  timestamp: string;
  levels: {
    price: number;
    bidSize: number;
    askSize: number;
    abuserSize?: number;
  }[];
};

const PRICE_BUCKET = 5;
const DEFAULT_VISIBLE_LEVELS = 22;
const LEFT_AXIS_WIDTH = 72;
const BOTTOM_AXIS_HEIGHT = 18;

type HeatmapTheme = {
  axis: string;
  background: string;
  dangerRgb: string;
  grid: string;
  infoRgb: string;
  lowCell: string;
  successRgb: string;
  warningRgb: string;
};

export function LiquidityHeatmap({
  maxFrames = 72,
  snapshots,
  visibleLevels = DEFAULT_VISIBLE_LEVELS
}: {
  maxFrames?: number;
  snapshots: OrderBookSnapshot[];
  visibleLevels?: number;
}) {
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [canvasSize, setCanvasSize] = useState({ height: 320, width: 900 });
  const [themeVersion, setThemeVersion] = useState(0);
  const frames = useMemo(() => toHeatmapFrames(snapshots.slice(-maxFrames)), [maxFrames, snapshots]);
  const visiblePrices = useMemo(() => getVisiblePrices(snapshots.at(-1), visibleLevels), [snapshots, visibleLevels]);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) {
      return;
    }

    const observer = new ResizeObserver(([entry]) => {
      const width = Math.max(320, Math.floor(entry.contentRect.width));
      const height = Math.max(260, Math.floor(entry.contentRect.height));
      setCanvasSize((current) => (
        current.width === width && current.height === height ? current : { height, width }
      ));
    });
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, []);


  useEffect(() => {
    const observer = new MutationObserver(() => setThemeVersion((version) => version + 1));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const pixelRatio = window.devicePixelRatio || 1;
    const nextWidth = Math.floor(canvasSize.width * pixelRatio);
    const nextHeight = Math.floor(canvasSize.height * pixelRatio);
    if (canvas.width !== nextWidth) {
      canvas.width = nextWidth;
    }
    if (canvas.height !== nextHeight) {
      canvas.height = nextHeight;
    }
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    drawHeatmap(context, frames, visiblePrices, readHeatmapTheme());
  }, [canvasSize, frames, themeVersion, visiblePrices]);

  return (
    <section className="liquidity-heatmap">
      <div className="section-heading-row">
        <h2>Liquidity Heatmap</h2>
        <span>{frames.length} frames</span>
      </div>
      <div className="heatmap-canvas-wrap" ref={wrapperRef}>
        <canvas
          ref={canvasRef}
          className="cockpit-heatmap"
          aria-label="Rolling liquidity heatmap by time frame and price level"
        />
      </div>
      <div className="heatmap-legend">
        <span><i className="legend-swatch low" /> dark = low liquidity</span>
        <span><i className="legend-swatch high" /> bright = high liquidity</span>
        <span><i className="legend-swatch abuser" /> outline = abuser liquidity</span>
      </div>
    </section>
  );
}

function drawHeatmap(context: CanvasRenderingContext2D, frames: HeatmapFrame[], visiblePrices: number[], theme: HeatmapTheme) {
  const { canvas } = context;
  const pixelRatio = window.devicePixelRatio || 1;
  const width = canvas.width / pixelRatio;
  const height = canvas.height / pixelRatio;
  const plotWidth = width - LEFT_AXIS_WIDTH;
  const plotHeight = height - BOTTOM_AXIS_HEIGHT;

  context.clearRect(0, 0, width, height);
  context.fillStyle = theme.background;
  context.fillRect(0, 0, width, height);

  if (!frames.length || !visiblePrices.length) {
    drawEmptyState(context, theme);
    return;
  }

  const maxDepth = Math.max(
    1,
    ...frames.flatMap((frame) => frame.levels.map((level) => level.bidSize + level.askSize))
  );
  const cellWidth = plotWidth / frames.length;
  const cellHeight = plotHeight / visiblePrices.length;

  drawYAxis(context, visiblePrices, cellHeight, theme);

  frames.forEach((frame, frameIndex) => {
    const levelsByPrice = new Map(frame.levels.map((level) => [level.price, level]));
    visiblePrices.forEach((price, priceIndex) => {
      const level = levelsByPrice.get(price);
      const depth = (level?.bidSize ?? 0) + (level?.askSize ?? 0);
      const intensity = Math.min(depth / maxDepth, 1);
      const x = LEFT_AXIS_WIDTH + frameIndex * cellWidth;
      const y = priceIndex * cellHeight;

      context.fillStyle = getCellColor(level, intensity, theme);
      context.fillRect(x, y, Math.max(1, cellWidth), Math.max(1, cellHeight));

      if ((level?.abuserSize ?? 0) > 0) {
        context.strokeStyle = `rgba(${theme.warningRgb}, 0.95)`;
        context.lineWidth = Math.max(1, Math.min(cellWidth, cellHeight) * 0.14);
        context.strokeRect(x + 0.5, y + 0.5, Math.max(1, cellWidth - 1), Math.max(1, cellHeight - 1));
      }
    });
  });

  drawXAxis(context, frames, plotWidth, plotHeight, theme);
}

function drawYAxis(context: CanvasRenderingContext2D, visiblePrices: number[], cellHeight: number, theme: HeatmapTheme) {
  context.fillStyle = theme.axis;
  context.font = "11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  visiblePrices.forEach((price, index) => {
    if (index % 3 !== 0 && index !== visiblePrices.length - 1) {
      return;
    }
    context.fillText(price.toLocaleString(), 4, index * cellHeight + cellHeight / 2 + 4);
  });
}

function drawXAxis(context: CanvasRenderingContext2D, frames: HeatmapFrame[], plotWidth: number, plotHeight: number, theme: HeatmapTheme) {
  context.strokeStyle = theme.grid;
  context.beginPath();
  context.moveTo(LEFT_AXIS_WIDTH, plotHeight + 0.5);
  context.lineTo(LEFT_AXIS_WIDTH + plotWidth, plotHeight + 0.5);
  context.stroke();

  context.fillStyle = theme.axis;
  context.font = "11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillText(frames[0]?.timestamp ?? "", LEFT_AXIS_WIDTH, plotHeight + 14);
  context.fillText(frames.at(-1)?.timestamp ?? "", LEFT_AXIS_WIDTH + plotWidth - 44, plotHeight + 14);
}

function drawEmptyState(context: CanvasRenderingContext2D, theme: HeatmapTheme) {
  context.fillStyle = theme.axis;
  context.font = "13px Inter, system-ui, sans-serif";
  context.fillText("Waiting for order-book frames", LEFT_AXIS_WIDTH, 34);
}

function getCellColor(level: HeatmapFrame["levels"][number] | undefined, intensity: number, theme: HeatmapTheme) {
  if (!level || intensity <= 0) {
    return theme.lowCell;
  }

  const alpha = 0.18 + intensity * 0.74;
  if (level.askSize > level.bidSize) {
    return `rgba(${theme.dangerRgb}, ${alpha})`;
  }
  if (level.bidSize > level.askSize) {
    return `rgba(${theme.successRgb}, ${alpha})`;
  }
  return `rgba(${theme.infoRgb}, ${alpha})`;
}

function readHeatmapTheme(): HeatmapTheme {
  const styles = getComputedStyle(document.documentElement);
  const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback;

  return {
    axis: read("--chart-axis", "#8fb7c9"),
    background: read("--chart-bg", "#050b12"),
    dangerRgb: read("--danger-rgb", "244, 63, 94"),
    grid: read("--chart-grid", "rgba(148, 163, 184, 0.16)"),
    infoRgb: read("--info-rgb", "34, 211, 238"),
    lowCell: read("--heatmap-low-cell", "rgba(15, 23, 42, 0.72)"),
    successRgb: read("--success-rgb", "16, 185, 129"),
    warningRgb: read("--warning-rgb", "251, 191, 36")
  };
}

function toHeatmapFrames(snapshots: OrderBookSnapshot[]): HeatmapFrame[] {
  return snapshots.map((snapshot, index) => {
    const levelsByPrice = new Map<number, HeatmapFrame["levels"][number]>();
    snapshot.bids.forEach((level) => mergeLevel(levelsByPrice, level, "bid"));
    snapshot.asks.forEach((level) => mergeLevel(levelsByPrice, level, "ask"));

    return {
      levels: Array.from(levelsByPrice.values()),
      timestamp: String(index + 1).padStart(3, "0")
    };
  });
}

function mergeLevel(
  levelsByPrice: Map<number, HeatmapFrame["levels"][number]>,
  level: PriceLevel,
  side: "ask" | "bid"
) {
  const price = bucketPrice(level.price);
  const existing = levelsByPrice.get(price) ?? { askSize: 0, bidSize: 0, price };

  if (side === "bid") {
    existing.bidSize += level.quantity;
  } else {
    existing.askSize += level.quantity;
  }

  if (isAbuserOwned(level)) {
    existing.abuserSize = (existing.abuserSize ?? 0) + level.quantity;
  }

  levelsByPrice.set(price, existing);
}

function getVisiblePrices(snapshot: OrderBookSnapshot | undefined, visibleLevels: number) {
  if (!snapshot?.mid) {
    return [];
  }

  const midpoint = bucketPrice(snapshot.mid);
  const halfLevels = Math.floor(visibleLevels / 2);
  return Array.from({ length: visibleLevels }, (_, index) => (
    midpoint + (halfLevels - index) * PRICE_BUCKET
  ));
}

function bucketPrice(price: number) {
  return Math.round(price / PRICE_BUCKET) * PRICE_BUCKET;
}

function isAbuserOwned(level: PriceLevel) {
  return level.owner === "abuser" || level.agent_id?.toLowerCase().includes("abuser");
}
