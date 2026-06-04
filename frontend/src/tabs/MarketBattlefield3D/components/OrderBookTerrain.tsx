import { useEffect, useRef } from "react";
import type { BattlefieldFrame } from "../types";

type OrderBookTerrainProps = {
  currentTick: number;
  frames: BattlefieldFrame[];
};

export function OrderBookTerrain({ currentTick, frames }: OrderBookTerrainProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return;
    }

    const resizeObserver = new ResizeObserver(() => drawTerrain(canvas, context, frames, currentTick));
    resizeObserver.observe(canvas);
    drawTerrain(canvas, context, frames, currentTick);
    return () => resizeObserver.disconnect();
  }, [currentTick, frames]);

  return (
    <section className="battlefield-terrain-panel">
      <div className="section-heading-row">
        <h2>3D Limit Order Book Terrain</h2>
        <span>liquidity as terrain | risk as heat</span>
      </div>
      <canvas ref={canvasRef} className="battlefield-terrain-canvas" aria-label="3D market battlefield terrain" />
      <div className="battlefield-legend">
        <span><i className="legend-swatch bid" /> bid liquidity</span>
        <span><i className="legend-swatch ask" /> ask liquidity</span>
        <span><i className="legend-swatch warning" /> imbalance pressure</span>
        <span><i className="legend-swatch attack" /> detected attack zone</span>
      </div>
    </section>
  );
}

function drawTerrain(
  canvas: HTMLCanvasElement,
  context: CanvasRenderingContext2D,
  frames: BattlefieldFrame[],
  currentTick: number
) {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  const width = Math.max(640, Math.floor(rect.width));
  const height = Math.max(420, Math.floor(rect.height));
  canvas.width = width * pixelRatio;
  canvas.height = height * pixelRatio;
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  context.clearRect(0, 0, width, height);
  drawBackground(context, width, height);

  const history = frames;
  const priceLevels = Array.from(new Set(history.flatMap((frame) => frame.cells.map((cell) => cell.priceLevel)))).sort((a, b) => a - b);
  const xStep = Math.min(22, Math.max(11, width / Math.max(34, priceLevels.length + 12)));
  const yStep = Math.min(13, Math.max(7, height / 78));
  const originX = width / 2;
  const originY = height * 0.72;
  const maxVolume = Math.max(1, ...history.flatMap((frame) => frame.cells.map((cell) => cell.volume)));

  drawFloorGrid(context, originX, originY, width, height, xStep, yStep);
  drawAxes(context, originX, originY, width, height, xStep);

  history.forEach((frame, frameIndex) => {
    const age = history.length - frameIndex;
    const timeOffset = age * yStep;
    const alpha = Math.max(0.16, 1 - age / 58);

    frame.cells.forEach((cell) => {
      if ((cell.side === "bid" && cell.priceLevel > 0) || (cell.side === "ask" && cell.priceLevel < 0)) {
        return;
      }
      const x = originX + cell.priceLevel * xStep;
      const y = originY - timeOffset + Math.abs(cell.priceLevel) * 1.6;
      const heightScale = Math.min(96, (cell.volume / maxVolume) * 104);
      drawTerrainPrism(context, x, y, heightScale, getCellColor(cell.anomalyScore, cell.side, alpha), cell.side);
    });
  });

  drawMidValley(context, originX, originY, history.length * yStep);
  drawScanner(context, originX, originY - history.length * yStep * 0.55, width, currentTick);
  drawAxisOverlay(context, width, height);
}

function drawBackground(context: CanvasRenderingContext2D, width: number, height: number) {
  const gradient = context.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, "#0a1624");
  gradient.addColorStop(1, "#04080d");
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);
}

function drawFloorGrid(
  context: CanvasRenderingContext2D,
  originX: number,
  originY: number,
  width: number,
  height: number,
  xStep: number,
  yStep: number
) {
  context.strokeStyle = "rgba(72, 108, 132, 0.18)";
  context.lineWidth = 1;
  for (let x = originX - xStep * 14; x <= originX + xStep * 14; x += xStep * 2) {
    context.beginPath();
    context.moveTo(x, originY + 24);
    context.lineTo(x + width * 0.18, height * 0.14);
    context.stroke();
  }
  for (let y = originY; y > height * 0.12; y -= yStep * 4) {
    context.beginPath();
    context.moveTo(width * 0.08, y);
    context.lineTo(width * 0.92, y);
    context.stroke();
  }
}

function drawAxes(
  context: CanvasRenderingContext2D,
  originX: number,
  originY: number,
  width: number,
  height: number,
  xStep: number
) {
  drawArrow(context, originX - xStep * 14, originY + 32, originX + xStep * 14, originY + 32, "#67e8f9");
  drawArrow(context, originX - xStep * 14, originY + 32, originX - xStep * 2, height * 0.16, "#a7f3d0");
  drawArrow(context, originX - xStep * 14, originY + 32, originX - xStep * 14, originY - 132, "#fde68a");

  context.font = "700 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillStyle = "#67e8f9";
  context.fillText("X: price levels around mid", originX + xStep * 8, originY + 54);
  context.fillStyle = "#a7f3d0";
  context.fillText("Y: ticks / time", originX - xStep * 3, height * 0.18);
  context.fillStyle = "#fde68a";
  context.fillText("Z: liquidity volume", originX - xStep * 14 - 8, originY - 144);
}

function drawArrow(
  context: CanvasRenderingContext2D,
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  color: string
) {
  const angle = Math.atan2(toY - fromY, toX - fromX);
  context.strokeStyle = color;
  context.fillStyle = color;
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(fromX, fromY);
  context.lineTo(toX, toY);
  context.stroke();
  context.beginPath();
  context.moveTo(toX, toY);
  context.lineTo(toX - Math.cos(angle - Math.PI / 6) * 10, toY - Math.sin(angle - Math.PI / 6) * 10);
  context.lineTo(toX - Math.cos(angle + Math.PI / 6) * 10, toY - Math.sin(angle + Math.PI / 6) * 10);
  context.closePath();
  context.fill();
}

function drawTerrainPrism(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  height: number,
  color: string,
  side: "ask" | "bid"
) {
  const width = 11;
  const skew = side === "ask" ? 5 : -5;
  const topY = y - height;

  context.fillStyle = shadeColor(color, 0.72);
  context.beginPath();
  context.moveTo(x - width / 2, y);
  context.lineTo(x + width / 2, y);
  context.lineTo(x + width / 2 + skew, topY + 5);
  context.lineTo(x - width / 2 + skew, topY + 5);
  context.closePath();
  context.fill();

  context.fillStyle = color;
  context.beginPath();
  context.moveTo(x - width / 2 + skew, topY + 5);
  context.lineTo(x + width / 2 + skew, topY + 5);
  context.lineTo(x + width / 2, topY);
  context.lineTo(x - width / 2, topY);
  context.closePath();
  context.fill();

  context.strokeStyle = "rgba(255, 255, 255, 0.18)";
  context.lineWidth = 1;
  context.stroke();
}

function drawAxisOverlay(context: CanvasRenderingContext2D, width: number, height: number) {
  context.fillStyle = "rgba(4, 10, 18, 0.72)";
  context.fillRect(14, 14, 230, 76);
  context.strokeStyle = "rgba(43, 90, 120, 0.6)";
  context.strokeRect(14.5, 14.5, 230, 76);
  context.font = "11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillStyle = "#67e8f9";
  context.fillText("X price levels", 28, 36);
  context.fillStyle = "#a7f3d0";
  context.fillText("Y simulation ticks", 28, 56);
  context.fillStyle = "#fde68a";
  context.fillText("Z visible liquidity", 28, 76);
  context.fillStyle = "rgba(143, 183, 201, 0.78)";
  context.fillText("live exchange order book", width - 190, height - 18);
}

function drawMidValley(context: CanvasRenderingContext2D, originX: number, originY: number, historyHeight: number) {
  context.strokeStyle = "rgba(103, 232, 249, 0.68)";
  context.lineWidth = 2;
  context.setLineDash([5, 6]);
  context.beginPath();
  context.moveTo(originX, originY + 18);
  context.lineTo(originX, originY - historyHeight - 20);
  context.stroke();
  context.setLineDash([]);
  context.fillStyle = "rgba(103, 232, 249, 0.9)";
  context.font = "11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillText("MID-PRICE VALLEY", originX + 10, originY - historyHeight - 16);
}

function drawScanner(context: CanvasRenderingContext2D, originX: number, y: number, width: number, tick: number) {
  const sweep = Math.sin(tick / 5) * width * 0.16;
  context.strokeStyle = "rgba(25, 167, 206, 0.72)";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(originX + sweep, y - 120);
  context.lineTo(originX - sweep, y + 170);
  context.stroke();
}

function getCellColor(anomalyScore: number, side: "ask" | "bid", alpha: number) {
  if (anomalyScore > 0.82) {
    return `rgba(104, 38, 180, ${Math.min(0.94, alpha + 0.18)})`;
  }
  if (anomalyScore > 0.58) {
    return `rgba(242, 54, 69, ${Math.min(0.92, alpha + 0.12)})`;
  }
  if (anomalyScore > 0.28) {
    return `rgba(245, 184, 65, ${Math.min(0.88, alpha + 0.08)})`;
  }
  return side === "bid" ? `rgba(34, 171, 148, ${alpha})` : `rgba(64, 156, 255, ${alpha})`;
}

function shadeColor(color: string, alphaMultiplier: number) {
  return color.replace(/rgba\(([^,]+), ([^,]+), ([^,]+), ([^)]+)\)/, (_match, red, green, blue, alpha) => (
    `rgba(${red}, ${green}, ${blue}, ${Number(alpha) * alphaMultiplier})`
  ));
}
