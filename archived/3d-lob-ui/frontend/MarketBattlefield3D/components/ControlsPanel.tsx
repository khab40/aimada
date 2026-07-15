import type { BattlefieldPlaybackState } from "../types";

export function ControlsPanel({
  maxTick,
  onPause,
  onPlay,
  onReset,
  onTickChange,
  playbackState,
  sliderValue,
  tick
}: {
  maxTick: number;
  onPause: () => void;
  onPlay: () => void;
  onReset: () => void;
  onTickChange: (tick: number) => void;
  playbackState: BattlefieldPlaybackState;
  sliderValue: number;
  tick: number;
}) {
  const playing = playbackState === "playing";

  return (
    <section className="battlefield-controls panel">
      <div className="section-heading-row">
        <h2>Replay Controls</h2>
        <span>exchange tick {tick}</span>
      </div>
      <div className="battlefield-control-buttons">
        <button disabled={playing} type="button" onClick={onPlay}>Play</button>
        <button disabled={!playing} type="button" onClick={onPause}>Pause</button>
        <button type="button" onClick={onReset}>Reset</button>
      </div>
      <label className="battlefield-slider">
        Simulation Tick
        <input
          max={maxTick}
          min={0}
          onChange={(event) => onTickChange(Number(event.target.value))}
          type="range"
          value={sliderValue}
        />
      </label>
    </section>
  );
}
