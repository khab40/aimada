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
  attack_started: "#fbbf24",
  detector_warning: "#f43f5e",
  incident_confirmed: "#10b981"
};

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
            <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={{ fontSize: 11, fill: "#8fb7c9" }} />
            <YAxis yAxisId="price" tick={{ fontSize: 11, fill: "#8fb7c9" }} domain={["dataMin - 10", "dataMax + 10"]} />
            <YAxis yAxisId="micro" orientation="right" tick={{ fontSize: 11, fill: "#8fb7c9" }} />
            <Tooltip contentStyle={{ background: "#071426", borderColor: "#1e3a5f", color: "#d8f3ff" }} />
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
            <Line yAxisId="price" type="monotone" dataKey="mid" name="mid price" stroke="#22d3ee" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line yAxisId="micro" type="monotone" dataKey="spreadBps" name="spread bps" stroke="#f59e0b" dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line yAxisId="micro" type="monotone" dataKey="imbalance" name="imbalance" stroke="#a78bfa" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="timeline-chart small" role="img" aria-label="Detector confidence timeline">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 4, right: 18, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" strokeDasharray="3 3" />
            <XAxis dataKey="tick" tick={{ fontSize: 10, fill: "#8fb7c9" }} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#8fb7c9" }} />
            <Tooltip contentStyle={{ background: "#071426", borderColor: "#1e3a5f", color: "#d8f3ff" }} />
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
              stroke="#f43f5e"
              fill="rgba(244, 63, 94, 0.24)"
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
