import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { DetectorScores, MarketFeatures } from "@/types/arena";

export type TimelineMarkerType = "attack_started" | "detector_warning" | "incident_confirmed";

export type MarketTimelineFrame = {
  detectorScores: DetectorScores;
  features: Partial<MarketFeatures>;
  markers?: TimelineMarkerType[];
  mid: number;
  tick: number;
};

type ChartPoint = {
  detectorConfidence: number;
  imbalance: number;
  mid: number;
  spreadBps: number;
  tick: number;
};

const markerLabels: Record<TimelineMarkerType, string> = {
  attack_started: "attack started",
  detector_warning: "detector warning",
  incident_confirmed: "incident confirmed"
};

const markerColors: Record<TimelineMarkerType, string> = {
  attack_started: "rgb(var(--warning-rgb))",
  detector_warning: "rgb(var(--danger-rgb))",
  incident_confirmed: "rgb(var(--success-rgb))"
};

const tooltipStyle = {
  background: "var(--chart-tooltip-bg)",
  borderColor: "var(--chart-tooltip-border)",
  color: "var(--chart-tooltip-text)"
};

const axisTick = { fontSize: 11, fill: "var(--chart-axis)" };
const smallAxisTick = { fontSize: 10, fill: "var(--chart-axis)" };

export function MarketTimeline({ frames }: { frames: MarketTimelineFrame[] }) {
  const points = frames.map(toChartPoint);
  const markers = getMarkers(frames);

  return (
    <section className="market-timeline">
      <div className="section-heading-row">
        <h2>Market Timeline</h2>
        <span>{points.length} frames</span>
      </div>

      <div className="timeline-chart" role="img" aria-label="Mid price, spread bps, and imbalance timeline">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 8, right: 18, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={axisTick} />
            <YAxis yAxisId="price" tick={axisTick} domain={["dataMin - 10", "dataMax + 10"]} />
            <YAxis yAxisId="micro" orientation="right" tick={axisTick} />
            <Tooltip contentStyle={tooltipStyle} />
            {markers.map((marker) => (
              <ReferenceLine
                ifOverflow="extendDomain"
                key={`${marker.type}-${marker.tick}`}
                label={{ fill: markerColors[marker.type], fontSize: 11, position: "top", value: markerLabels[marker.type] }}
                stroke={markerColors[marker.type]}
                strokeDasharray="4 4"
                x={marker.tick}
                yAxisId="price"
              />
            ))}
            <Line yAxisId="price" type="monotone" dataKey="mid" name="mid price" stroke="var(--chart-line-primary)" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line yAxisId="micro" type="monotone" dataKey="spreadBps" name="spread bps" stroke="var(--chart-line-warning)" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line yAxisId="micro" type="monotone" dataKey="imbalance" name="imbalance" stroke="var(--chart-line-violet)" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="timeline-chart small" role="img" aria-label="Detector confidence timeline">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 4, right: 18, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={smallAxisTick} />
            <YAxis domain={[0, 1]} tick={smallAxisTick} />
            <Tooltip contentStyle={tooltipStyle} />
            {markers.map((marker) => (
              <ReferenceLine
                ifOverflow="extendDomain"
                key={`detector-${marker.type}-${marker.tick}`}
                stroke={markerColors[marker.type]}
                strokeDasharray="4 4"
                x={marker.tick}
              />
            ))}
            <Area
              type="monotone"
              dataKey="detectorConfidence"
              name="detector confidence"
              stroke="rgb(var(--danger-rgb))"
              fill="rgba(var(--danger-rgb), 0.24)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function toChartPoint(frame: MarketTimelineFrame): ChartPoint {
  return {
    detectorConfidence: Math.max(0, ...frame.detectorScores.scores.map((score) => score.confidence)),
    imbalance: frame.features.imbalance ?? 0,
    mid: frame.mid,
    spreadBps: frame.features.spread_bps ?? 0,
    tick: frame.tick
  };
}

function getMarkers(frames: MarketTimelineFrame[]) {
  const seen = new Set<TimelineMarkerType>();
  return frames.flatMap((frame) => (
    (frame.markers ?? []).flatMap((type) => {
      if (seen.has(type)) {
        return [];
      }
      seen.add(type);
      return [{ tick: frame.tick, type }];
    })
  ));
}
