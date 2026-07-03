import { useEffect, useRef, useState, type PointerEvent } from "react";
import type { BattlefieldCell, BattlefieldEvent, BattlefieldFrame } from "../types";

type OrderBookTerrainProps = {
  currentTick: number;
  frames: BattlefieldFrame[];
};

type CameraState = {
  panX: number;
  panY: number;
  pitch: number;
  yaw: number;
  zoom: number;
};

type HitTarget = {
  cell: BattlefieldCell;
  height: number;
  x: number;
  y: number;
};

const DEFAULT_CAMERA: CameraState = {
  panX: 0,
  panY: 0,
  pitch: 0.64,
  yaw: 0.1,
  zoom: 1
};

const MIN_ZOOM = 0.78;
const MAX_ZOOM = 1.34;

export function OrderBookTerrain({ currentTick, frames }: OrderBookTerrainProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cameraRef = useRef<CameraState>({ ...DEFAULT_CAMERA });
  const targetCameraRef = useRef<CameraState>({ ...DEFAULT_CAMERA });
  const hitTargetsRef = useRef<HitTarget[]>([]);
  const animationRef = useRef<number | null>(null);
  const latestRef = useRef({ currentTick, frames });
  const [autoOrbit, setAutoOrbit] = useState(false);
  const [cameraPaused, setCameraPaused] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<BattlefieldCell | null>(null);
  const [zoom, setZoom] = useState(DEFAULT_CAMERA.zoom);

  useEffect(() => {
    latestRef.current = { currentTick, frames };
  }, [currentTick, frames]);

  useEffect(() => {
    targetCameraRef.current.zoom = clamp(zoom, MIN_ZOOM, MAX_ZOOM);
  }, [zoom]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) {
      return undefined;
    }

    const resizeObserver = new ResizeObserver(() => resizeCanvas(canvas));
    resizeObserver.observe(canvas);
    resizeCanvas(canvas);

    const render = (timestamp: number) => {
      if (autoOrbit && !cameraPaused) {
        targetCameraRef.current.yaw = DEFAULT_CAMERA.yaw + Math.sin(timestamp / 6200) * 0.08;
      }
      if (!cameraPaused) {
        interpolateCamera(cameraRef.current, targetCameraRef.current, 0.075);
      }
      const nextHits = drawTerrain(
        canvas,
        context,
        latestRef.current.frames,
        latestRef.current.currentTick,
        cameraRef.current,
        hoveredCell,
        cameraPaused
      );
      hitTargetsRef.current = nextHits;
      animationRef.current = window.requestAnimationFrame(render);
    };

    animationRef.current = window.requestAnimationFrame(render);
    return () => {
      resizeObserver.disconnect();
      if (animationRef.current !== null) {
        window.cancelAnimationFrame(animationRef.current);
      }
    };
  }, [autoOrbit, cameraPaused, hoveredCell]);

  function resetCamera() {
    targetCameraRef.current = { ...DEFAULT_CAMERA };
    cameraRef.current = { ...DEFAULT_CAMERA };
    setAutoOrbit(false);
    setCameraPaused(false);
    setZoom(DEFAULT_CAMERA.zoom);
  }

  function focusSuspicious() {
    targetCameraRef.current = {
      panX: 0,
      panY: 10,
      pitch: 0.68,
      yaw: 0.14,
      zoom: 1.16
    };
    setZoom(1.16);
  }

  function handlePointerMove(event: PointerEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const target = hitTargetsRef.current
      .filter((item) => item.cell.state !== "normal")
      .find((item) => Math.abs(item.x - x) <= 16 && y <= item.y + 12 && y >= item.y - item.height - 22);
    setHoveredCell(target?.cell ?? null);
  }

  return (
    <section className="battlefield-terrain-panel">
      <div className="section-heading-row">
        <h2>3D Limit Order Book Terrain</h2>
        <span>liquidity as terrain | risk as heat</span>
      </div>
      <div className="battlefield-camera-controls" aria-label="Battlefield camera controls">
        <button className={autoOrbit ? "active" : ""} onClick={() => setAutoOrbit((value) => !value)} type="button">
          Auto orbit
        </button>
        <button className={cameraPaused ? "active" : ""} onClick={() => setCameraPaused((value) => !value)} type="button">
          {cameraPaused ? "Resume camera" : "Pause camera"}
        </button>
        <button onClick={resetCamera} type="button">Reset camera</button>
        <button onClick={focusSuspicious} type="button">Focus alerts</button>
        <label>
          Zoom
          <input
            max={MAX_ZOOM}
            min={MIN_ZOOM}
            onChange={(event) => setZoom(Number(event.target.value))}
            step="0.02"
            type="range"
            value={zoom}
          />
        </label>
      </div>
      <canvas
        ref={canvasRef}
        className="battlefield-terrain-canvas"
        aria-label="3D market battlefield terrain"
        onPointerLeave={() => setHoveredCell(null)}
        onPointerMove={handlePointerMove}
      />
      <div className="battlefield-legend">
        <span><i className="legend-swatch bid" /> Bid</span>
        <span><i className="legend-swatch ask" /> Ask</span>
        <span><i className="legend-swatch suspicious" /> Suspicious</span>
        <span><i className="legend-swatch cancelled" /> Cancelled</span>
        <span><i className="legend-swatch trade" /> Trade</span>
        <span><i className="legend-swatch path" /> Manipulation path</span>
        <span><i className="legend-swatch attack" /> Alert zone</span>
      </div>
    </section>
  );
}

function resizeCanvas(canvas: HTMLCanvasElement) {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  const width = Math.max(640, Math.floor(rect.width));
  const height = Math.max(420, Math.floor(rect.height));
  canvas.width = width * pixelRatio;
  canvas.height = height * pixelRatio;
}

function drawTerrain(
  canvas: HTMLCanvasElement,
  context: CanvasRenderingContext2D,
  frames: BattlefieldFrame[],
  currentTick: number,
  camera: CameraState,
  hoveredCell: BattlefieldCell | null,
  paused: boolean
) {
  const pixelRatio = window.devicePixelRatio || 1;
  const width = canvas.width / pixelRatio;
  const height = canvas.height / pixelRatio;
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, width, height);
  drawBackground(context, width, height);

  const history = frames.slice(-54);
  const priceLevels = Array.from(new Set(history.flatMap((frame) => frame.cells.map((cell) => cell.priceLevel)))).sort((a, b) => a - b);
  const xStep = Math.min(24, Math.max(12, width / Math.max(34, priceLevels.length + 12))) * camera.zoom;
  const yStep = Math.min(13, Math.max(7, height / 78)) * (0.9 + camera.pitch * 0.12);
  const originX = width / 2 + camera.panX;
  const originY = height * 0.72 + camera.panY;
  const maxVolume = Math.max(1, ...history.flatMap((frame) => frame.cells.map((cell) => cell.volume)));
  const alertConfidence = Math.max(0, ...history.map((frame) => frame.spoofingProbability));
  const hitTargets: HitTarget[] = [];
  const manipulationPath: Array<{ risk: number; state: BattlefieldCell["state"]; x: number; y: number }> = [];

  drawFloorGrid(context, originX, originY, width, height, xStep, yStep, camera);
  drawAxes(context, originX, originY, width, height, xStep, camera);
  if (alertConfidence > 0.62) {
    drawDetectorAlertZone(context, originX, originY, width, history.length * yStep, alertConfidence, currentTick, camera);
  }

  history.forEach((frame, frameIndex) => {
    const age = history.length - frameIndex;
    const timeOffset = age * yStep;
    const alpha = Math.max(0.2, 1 - age / 62);

    frame.cells.forEach((cell) => {
      if ((cell.side === "bid" && cell.priceLevel > 0) || (cell.side === "ask" && cell.priceLevel < 0)) {
        return;
      }
      const point = projectCell(cell, originX, originY, xStep, timeOffset, camera);
      const heightScale = Math.min(100, (cell.volume / maxVolume) * 106) * camera.zoom * (0.86 + camera.pitch * 0.18);
      const focused = Boolean(hoveredCell && hoveredCell.tick === cell.tick && hoveredCell.priceLevel === cell.priceLevel && hoveredCell.side === cell.side);
      drawTerrainPrism(context, point.x, point.y, heightScale, getCellColor(cell, alpha), cell.side, cell.state ?? "normal", focused);
      if (cell.state !== "normal" || cell.anomalyScore > 0.58) {
        hitTargets.push({ cell, height: heightScale, x: point.x, y: point.y });
        manipulationPath.push({ risk: cell.anomalyScore, state: cell.state, x: point.x, y: point.y - heightScale - 5 });
      }
      if (cell.state === "cancelled") {
        drawCancelMarker(context, point.x, point.y - heightScale - 9);
      } else if (cell.state === "trade") {
        drawTradeMarker(context, point.x, point.y - heightScale - 9);
      }
    });
  });

  drawManipulationPath(context, manipulationPath);
  drawEventMarkers(context, history.at(-1)?.events ?? [], originX, originY, xStep, camera);
  drawMidValley(context, originX, originY, history.length * yStep, camera);
  drawScanner(context, originX, originY - history.length * yStep * 0.55, width, currentTick, paused);
  drawAxisOverlay(context, width, height, camera, hoveredCell);
  return hitTargets;
}

function projectCell(
  cell: BattlefieldCell,
  originX: number,
  originY: number,
  xStep: number,
  timeOffset: number,
  camera: CameraState
) {
  return {
    x: originX + cell.priceLevel * xStep + timeOffset * camera.yaw * 0.42,
    y: originY - timeOffset * (0.75 + camera.pitch * 0.2) + Math.abs(cell.priceLevel) * (0.9 + camera.pitch * 1.15)
  };
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
  yStep: number,
  camera: CameraState
) {
  drawSideBands(context, originX, originY, width, height, xStep, yStep, camera);
  drawDepthHaze(context, width, height);
  context.strokeStyle = "rgba(72, 108, 132, 0.18)";
  context.lineWidth = 1;
  for (let x = originX - xStep * 14; x <= originX + xStep * 14; x += xStep * 2) {
    context.beginPath();
    context.moveTo(x, originY + 24);
    context.lineTo(x + width * (0.12 + camera.yaw * 0.4), height * 0.15);
    context.stroke();
  }
  for (let y = originY; y > height * 0.12; y -= yStep * 4) {
    context.beginPath();
    context.moveTo(width * 0.08, y);
    context.lineTo(width * 0.92, y + camera.yaw * 30);
    context.stroke();
  }
  drawPriceLevelLabels(context, originX, originY, xStep, camera);
  drawTimeDirection(context, originX, originY, historyDepth(yStep), xStep, camera);
}

function drawSideBands(
  context: CanvasRenderingContext2D,
  originX: number,
  originY: number,
  width: number,
  height: number,
  xStep: number,
  yStep: number,
  camera: CameraState
) {
  const topY = height * 0.15;
  const leftSkew = width * (0.1 + camera.yaw * 0.35);
  const rightSkew = width * (0.12 + camera.yaw * 0.35);
  const askGradient = context.createLinearGradient(originX, 0, originX + xStep * 14, 0);
  askGradient.addColorStop(0, "rgba(64, 156, 255, 0.03)");
  askGradient.addColorStop(1, "rgba(64, 156, 255, 0.12)");
  context.fillStyle = askGradient;
  context.beginPath();
  context.moveTo(originX, originY + 28);
  context.lineTo(originX + xStep * 14, originY + 28);
  context.lineTo(originX + xStep * 14 + rightSkew, topY);
  context.lineTo(originX + leftSkew * 0.35, topY);
  context.closePath();
  context.fill();

  const bidGradient = context.createLinearGradient(originX - xStep * 14, 0, originX, 0);
  bidGradient.addColorStop(0, "rgba(34, 171, 148, 0.12)");
  bidGradient.addColorStop(1, "rgba(34, 171, 148, 0.03)");
  context.fillStyle = bidGradient;
  context.beginPath();
  context.moveTo(originX - xStep * 14, originY + 28);
  context.lineTo(originX, originY + 28);
  context.lineTo(originX + leftSkew * 0.35, topY);
  context.lineTo(originX - xStep * 14 + leftSkew, topY);
  context.closePath();
  context.fill();

  context.strokeStyle = "rgba(143, 183, 201, 0.34)";
  context.setLineDash([5, 7]);
  context.beginPath();
  context.moveTo(originX, originY + 34);
  context.lineTo(originX + camera.yaw * 72, topY - yStep);
  context.stroke();
  context.setLineDash([]);

  context.font = "700 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillStyle = "rgba(167, 243, 208, 0.88)";
  context.fillText("BID SIDE", originX - xStep * 12, originY + 52);
  context.fillStyle = "rgba(147, 197, 253, 0.9)";
  context.fillText("ASK SIDE", originX + xStep * 9, originY + 52);
}

function drawPriceLevelLabels(context: CanvasRenderingContext2D, originX: number, originY: number, xStep: number, camera: CameraState) {
  context.font = "10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.textAlign = "center";
  [-12, -8, -4, 0, 4, 8, 12].forEach((level) => {
    const x = originX + level * xStep;
    const label = level === 0 ? "MID" : `${level > 0 ? "+" : ""}${level}`;
    context.fillStyle = level < 0 ? "rgba(167, 243, 208, 0.72)" : level > 0 ? "rgba(147, 197, 253, 0.74)" : "rgba(226, 232, 240, 0.9)";
    context.fillText(label, x + camera.yaw * 6, originY + 72);
  });
  context.textAlign = "start";
}

function drawTimeDirection(context: CanvasRenderingContext2D, originX: number, originY: number, depth: number, xStep: number, camera: CameraState) {
  const fromX = originX - 13.5 * xStep + camera.yaw * 62;
  const fromY = originY - depth * 0.86;
  const toX = originX - 13.5 * xStep;
  const toY = originY + 12;
  drawArrow(context, fromX, fromY, toX, toY, "rgba(167, 243, 208, 0.68)");
  context.fillStyle = "rgba(167, 243, 208, 0.78)";
  context.font = "700 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillText("TIME -> LATEST", fromX - 4, fromY - 10);
}

function drawDepthHaze(context: CanvasRenderingContext2D, width: number, height: number) {
  const haze = context.createLinearGradient(0, 0, 0, height * 0.62);
  haze.addColorStop(0, "rgba(4, 8, 13, 0.42)");
  haze.addColorStop(0.5, "rgba(4, 8, 13, 0.08)");
  haze.addColorStop(1, "rgba(4, 8, 13, 0)");
  context.fillStyle = haze;
  context.fillRect(0, 0, width, height * 0.62);
}

function historyDepth(yStep: number) {
  return 54 * yStep;
}

function drawAxes(
  context: CanvasRenderingContext2D,
  originX: number,
  originY: number,
  width: number,
  height: number,
  xStep: number,
  camera: CameraState
) {
  drawArrow(context, originX - xStep * 14, originY + 32, originX + xStep * 14, originY + 32, "#67e8f9");
  drawArrow(context, originX - xStep * 14, originY + 32, originX - xStep * 2 + camera.yaw * 52, height * 0.16, "#a7f3d0");
  drawArrow(context, originX - xStep * 14, originY + 32, originX - xStep * 14, originY - 132 * camera.zoom, "#fde68a");

  context.font = "700 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillStyle = "#67e8f9";
  context.fillText("X: price levels around mid", originX + xStep * 8, originY + 54);
  context.fillStyle = "#a7f3d0";
  context.fillText("Y: ticks / time", originX - xStep * 3, height * 0.18);
  context.fillStyle = "#fde68a";
  context.fillText("Z: liquidity volume", originX - xStep * 14 - 8, originY - 144 * camera.zoom);
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
  side: "ask" | "bid",
  state: BattlefieldCell["state"],
  focused: boolean
) {
  const width = focused ? 15 : 11;
  const skew = side === "ask" ? 5 : -5;
  const topY = y - height;

  context.fillStyle = shadeColor(color, 0.7);
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

  context.strokeStyle = state === "alert" || focused ? "rgba(255, 255, 255, 0.78)" : "rgba(255, 255, 255, 0.18)";
  context.lineWidth = focused ? 2 : 1;
  context.stroke();

  if (state === "suspicious" || state === "alert") {
    context.strokeStyle = state === "alert" ? "rgba(248, 113, 113, 0.9)" : "rgba(251, 191, 36, 0.76)";
    context.lineWidth = 2;
    context.beginPath();
    context.ellipse(x, topY + 2, 13, 5, 0, 0, Math.PI * 2);
    context.stroke();
  }
}

function drawDetectorAlertZone(
  context: CanvasRenderingContext2D,
  originX: number,
  originY: number,
  width: number,
  historyHeight: number,
  confidence: number,
  tick: number,
  camera: CameraState
) {
  const zoneWidth = width * 0.3 * camera.zoom;
  const pulse = 0.5 + Math.sin(tick / 7) * 0.5;
  const gradient = context.createLinearGradient(originX - zoneWidth / 2, 0, originX + zoneWidth / 2, 0);
  gradient.addColorStop(0, "rgba(248, 113, 113, 0)");
  gradient.addColorStop(0.5, `rgba(248, 113, 113, ${0.1 + confidence * 0.14 + pulse * 0.04})`);
  gradient.addColorStop(1, "rgba(248, 113, 113, 0)");
  context.fillStyle = gradient;
  context.beginPath();
  context.moveTo(originX - zoneWidth / 2 + camera.yaw * 70, originY + 20);
  context.lineTo(originX + zoneWidth / 2 + camera.yaw * 70, originY + 20);
  context.lineTo(originX + zoneWidth * 0.36, originY - historyHeight - 46);
  context.lineTo(originX - zoneWidth * 0.36, originY - historyHeight - 46);
  context.closePath();
  context.fill();
  context.strokeStyle = `rgba(248, 113, 113, ${0.38 + pulse * 0.28})`;
  context.stroke();
  context.strokeStyle = `rgba(251, 191, 36, ${0.12 + pulse * 0.22})`;
  context.lineWidth = 2;
  context.beginPath();
  context.ellipse(originX + camera.yaw * 32, originY - historyHeight * 0.42, zoneWidth * (0.16 + pulse * 0.06), 22 + pulse * 8, 0, 0, Math.PI * 2);
  context.stroke();
  context.fillStyle = "rgba(248, 113, 113, 0.88)";
  context.font = "700 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillText("DETECTOR ALERT ZONE", originX + zoneWidth * 0.18, originY - historyHeight - 54);
}

function drawManipulationPath(
  context: CanvasRenderingContext2D,
  path: Array<{ risk: number; state: BattlefieldCell["state"]; x: number; y: number }>
) {
  const points = path
    .filter((point) => point.risk > 0.58 || point.state === "cancelled" || point.state === "alert")
    .slice(-34);
  if (points.length < 2) {
    return;
  }
  context.save();
  context.strokeStyle = "rgba(251, 191, 36, 0.74)";
  context.lineWidth = 2;
  context.setLineDash([8, 6]);
  context.beginPath();
  points.forEach((point, index) => {
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  });
  context.stroke();
  context.setLineDash([]);
  points.forEach((point, index) => {
    const radius = point.state === "alert" ? 4.6 : point.state === "cancelled" ? 3.8 : 3;
    context.fillStyle = index === points.length - 1 ? "rgba(248, 113, 113, 0.92)" : "rgba(251, 191, 36, 0.78)";
    context.beginPath();
    context.arc(point.x, point.y, radius, 0, Math.PI * 2);
    context.fill();
  });
  const last = points.at(-1);
  if (last) {
    context.fillStyle = "rgba(251, 191, 36, 0.86)";
    context.font = "700 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
    context.fillText("LAYERING / SPOOFING PATH", last.x + 10, last.y - 8);
  }
  context.restore();
}

function drawCancelMarker(context: CanvasRenderingContext2D, x: number, y: number) {
  context.strokeStyle = "rgba(248, 113, 113, 0.96)";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(x - 7, y - 7);
  context.lineTo(x + 7, y + 7);
  context.moveTo(x + 7, y - 7);
  context.lineTo(x - 7, y + 7);
  context.stroke();
}

function drawTradeMarker(context: CanvasRenderingContext2D, x: number, y: number) {
  context.fillStyle = "rgba(103, 232, 249, 0.96)";
  context.beginPath();
  context.moveTo(x, y - 8);
  context.lineTo(x + 8, y);
  context.lineTo(x, y + 8);
  context.lineTo(x - 8, y);
  context.closePath();
  context.fill();
}

function drawEventMarkers(
  context: CanvasRenderingContext2D,
  events: BattlefieldEvent[],
  originX: number,
  originY: number,
  xStep: number,
  camera: CameraState
) {
  events.slice(0, 8).forEach((event, index) => {
    const x = originX + (index - 3.5) * xStep * 1.5;
    const y = originY - 248 - index * 12 + camera.yaw * 48;
    if (event.type === "DETECTION") {
      context.fillStyle = "rgba(248, 113, 113, 0.92)";
      context.fillRect(x - 30, y - 9, 60, 18);
      context.fillStyle = "#fff1f2";
      context.font = "700 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
      context.fillText("ALERT", x - 15, y + 4);
    } else if (event.type === "CANCEL_BURST") {
      drawCancelMarker(context, x, y);
    } else if (event.type === "PRICE_MOVE") {
      drawTradeMarker(context, x, y);
    }
  });
}

function drawAxisOverlay(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  camera: CameraState,
  hoveredCell: BattlefieldCell | null
) {
  context.fillStyle = "rgba(4, 10, 18, 0.74)";
  context.fillRect(14, 14, 268, hoveredCell ? 118 : 88);
  context.strokeStyle = "rgba(43, 90, 120, 0.6)";
  context.strokeRect(14.5, 14.5, 268, hoveredCell ? 118 : 88);
  context.font = "11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillStyle = "#67e8f9";
  context.fillText(`Camera yaw ${camera.yaw.toFixed(2)} | zoom ${camera.zoom.toFixed(2)}`, 28, 36);
  context.fillStyle = "#a7f3d0";
  context.fillText("Normal orders: green / blue prisms", 28, 56);
  context.fillStyle = "#fde68a";
  context.fillText("Suspicious orders: amber/red rings", 28, 76);
  if (hoveredCell) {
    context.fillStyle = "#fda4af";
    context.fillText(`${hoveredCell.state ?? "order"} ${hoveredCell.side} ${hoveredCell.price?.toFixed(2) ?? ""}`, 28, 100);
    context.fillText(`size ${hoveredCell.volume.toFixed(3)} | risk ${hoveredCell.anomalyScore.toFixed(2)}`, 28, 118);
  }
  context.fillStyle = "rgba(143, 183, 201, 0.78)";
  context.fillText("live exchange order book", width - 190, height - 18);
}

function drawMidValley(context: CanvasRenderingContext2D, originX: number, originY: number, historyHeight: number, camera: CameraState) {
  context.strokeStyle = "rgba(103, 232, 249, 0.68)";
  context.lineWidth = 2;
  context.setLineDash([5, 6]);
  context.beginPath();
  context.moveTo(originX, originY + 18);
  context.lineTo(originX + camera.yaw * 72, originY - historyHeight - 20);
  context.stroke();
  context.setLineDash([]);
  context.fillStyle = "rgba(103, 232, 249, 0.9)";
  context.font = "11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  context.fillText("MID-PRICE VALLEY", originX + 10 + camera.yaw * 72, originY - historyHeight - 16);
}

function drawScanner(context: CanvasRenderingContext2D, originX: number, y: number, width: number, tick: number, paused: boolean) {
  const sweep = paused ? 0 : Math.sin(tick / 9) * width * 0.1;
  context.strokeStyle = "rgba(25, 167, 206, 0.48)";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(originX + sweep, y - 96);
  context.lineTo(originX - sweep, y + 150);
  context.stroke();
}

function getCellColor(cell: BattlefieldCell, alpha: number) {
  switch (cell.state) {
    case "alert":
      return `rgba(225, 29, 72, ${Math.min(0.96, alpha + 0.22)})`;
    case "cancelled":
      return `rgba(148, 163, 184, ${Math.min(0.9, alpha + 0.1)})`;
    case "suspicious":
      return `rgba(245, 158, 11, ${Math.min(0.94, alpha + 0.16)})`;
    case "trade":
      return `rgba(103, 232, 249, ${Math.min(0.88, alpha + 0.08)})`;
    default:
      if (cell.anomalyScore > 0.58) {
        return `rgba(245, 184, 65, ${Math.min(0.88, alpha + 0.08)})`;
      }
      return cell.side === "bid" ? `rgba(34, 171, 148, ${alpha})` : `rgba(64, 156, 255, ${alpha})`;
  }
}

function shadeColor(color: string, alphaMultiplier: number) {
  return color.replace(/rgba\(([^,]+), ([^,]+), ([^,]+), ([^)]+)\)/, (_match, red, green, blue, alpha) => (
    `rgba(${red}, ${green}, ${blue}, ${Number(alpha) * alphaMultiplier})`
  ));
}

function interpolateCamera(current: CameraState, target: CameraState, factor: number) {
  current.panX += (target.panX - current.panX) * factor;
  current.panY += (target.panY - current.panY) * factor;
  current.pitch += (target.pitch - current.pitch) * factor;
  current.yaw += (target.yaw - current.yaw) * factor;
  current.zoom += (target.zoom - current.zoom) * factor;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
