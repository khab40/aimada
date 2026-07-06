import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { launchAttackExperiment, saveAttackExperiment, type AttackExperimentRequest } from "@/api/client";
import { featureFlags } from "@/featureFlags";
import type { ArenaScenarioType } from "@/hooks/useArenaSource";

type CancelStyle = "instant" | "gradual" | "partial";
type Difficulty = "Easy" | "Medium" | "Hard";
type NoiseCover = "none" | "low" | "high";

const scenarioTypes = ["spoofing", "layering", "quote stuffing", "liquidity evaporation"];
const cancelStyles: CancelStyle[] = ["instant", "gradual", "partial"];
const noiseCovers: NoiseCover[] = ["none", "low", "high"];

export function AttackBuilder({ onLaunchScenario }: { onLaunchScenario?: (type: ArenaScenarioType) => void }) {
  const [cancelStyle, setCancelStyle] = useState<CancelStyle>("instant");
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [distanceFromMidBps, setDistanceFromMidBps] = useState(12);
  const [lifetimeSeconds, setLifetimeSeconds] = useState(5);
  const [noiseCover, setNoiseCover] = useState<NoiseCover>("low");
  const [scenarioType, setScenarioType] = useState("spoofing");
  const [savedCount, setSavedCount] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [wallSizeMultiplier, setWallSizeMultiplier] = useState(8);

  const risk = useMemo(() => calculateRisk({
    cancelStyle,
    distanceFromMidBps,
    lifetimeSeconds,
    noiseCover,
    scenarioType,
    wallSizeMultiplier
  }), [cancelStyle, distanceFromMidBps, lifetimeSeconds, noiseCover, scenarioType, wallSizeMultiplier]);

  const request = useMemo<AttackExperimentRequest>(() => ({
    cancel_style: cancelStyle,
    distance_from_mid_bps: distanceFromMidBps,
    lifetime_seconds: lifetimeSeconds,
    noise_cover: noiseCover,
    predicted_detection_risk: risk.score,
    scenario_type: scenarioType,
    wall_size_multiplier: wallSizeMultiplier
  }), [cancelStyle, distanceFromMidBps, lifetimeSeconds, noiseCover, risk.score, scenarioType, wallSizeMultiplier]);

  async function handleLaunch() {
    if (onLaunchScenario) {
      onLaunchScenario(toArenaScenarioType(scenarioType));
      setStatusMessage(`Launched ${scenarioType} in Arena.`);
      return;
    }

    setIsSubmitting(true);
    setStatusMessage("Launching scenario in Arena...");
    try {
      const result = await launchAttackExperiment(request);
      setStatusMessage(`Launched ${scenarioType}. Experiment ${result.experiment_id} persisted.`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Launch failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleDifficultyChange(nextDifficulty: Difficulty) {
    setDifficulty(nextDifficulty);
    if (nextDifficulty === "Easy") {
      setWallSizeMultiplier(5);
      setDistanceFromMidBps(24);
      setNoiseCover("high");
      return;
    }
    if (nextDifficulty === "Hard") {
      setWallSizeMultiplier(12);
      setDistanceFromMidBps(8);
      setNoiseCover("none");
      return;
    }
    setWallSizeMultiplier(8);
    setDistanceFromMidBps(12);
    setNoiseCover("low");
  }

  async function handleSave() {
    setIsSubmitting(true);
    setStatusMessage("Saving experiment...");
    try {
      const result = await saveAttackExperiment(request);
      setSavedCount((count) => count + 1);
      setStatusMessage(`Saved ${result.id}.`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Save failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="attack-builder">
      <div className="section-heading-row">
        <div>
          <h2>Scenario Setup</h2>
        </div>
        <span className={`risk-chip ${risk.label.toLowerCase()}`}>{risk.label} risk</span>
      </div>

      <div className="attack-builder-grid">
        <label className="form-row">
          Manipulation type
          <select value={scenarioType} onChange={(event) => setScenarioType(event.target.value)}>
            {scenarioTypes.map((scenario) => <option key={scenario}>{scenario}</option>)}
          </select>
        </label>

        <label className="form-row">
          Difficulty
          <select value={difficulty} onChange={(event) => handleDifficultyChange(event.target.value as Difficulty)}>
            {["Easy", "Medium", "Hard"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>

        <label className="form-row">
          Duration
          <input
            max={15}
            min={1}
            onChange={(event) => setLifetimeSeconds(Number(event.target.value))}
            type="range"
            value={lifetimeSeconds}
          />
          <strong>{lifetimeSeconds}s</strong>
        </label>
      </div>

      {featureFlags.enableAdvancedAttackControls ? (
        <details className="scenario-advanced-panel">
          <summary>Advanced attack tuning</summary>
          <div className="attack-builder-grid">
            <label className="form-row">
              Wall size multiplier
              <input
                max={20}
                min={1}
                onChange={(event) => setWallSizeMultiplier(Number(event.target.value))}
                type="range"
                value={wallSizeMultiplier}
              />
              <strong>{wallSizeMultiplier.toFixed(1)}x</strong>
            </label>

            <label className="form-row">
              Distance from mid bps
              <input
                max={60}
                min={1}
                onChange={(event) => setDistanceFromMidBps(Number(event.target.value))}
                type="range"
                value={distanceFromMidBps}
              />
              <strong>{distanceFromMidBps} bps</strong>
            </label>

            <label className="form-row">
              Cancel style
              <select value={cancelStyle} onChange={(event) => setCancelStyle(event.target.value as CancelStyle)}>
                {cancelStyles.map((style) => <option key={style}>{style}</option>)}
              </select>
            </label>

            <label className="form-row">
              Noise cover
              <select value={noiseCover} onChange={(event) => setNoiseCover(event.target.value as NoiseCover)}>
                {noiseCovers.map((cover) => <option key={cover}>{cover}</option>)}
              </select>
            </label>
          </div>
        </details>
      ) : null}

      <div className="attack-risk-panel">
        <div className="risk-meter-track">
          <div style={{ width: `${risk.score * 100}%` }} />
        </div>
        <p>{risk.explanation}</p>
      </div>

      <div className="attack-builder-actions">
        <button disabled={isSubmitting} type="button" onClick={() => void handleLaunch()}>
          Run scenario
        </button>
        <Link className="primary-link-button" to="/investigations">
          Send to Nebius investigation
        </Link>
        {featureFlags.enableAdvancedAttackControls ? (
          <button disabled={isSubmitting} type="button" onClick={() => void handleSave()}>
            Save as experiment
          </button>
        ) : null}
        {featureFlags.enableAdvancedAttackControls && savedCount > 0 ? <span>{savedCount} saved</span> : null}
        {statusMessage ? <span>{statusMessage}</span> : null}
      </div>
    </section>
  );
}

function toArenaScenarioType(value: string): ArenaScenarioType {
  const normalized = value.toLowerCase().replaceAll("-", " ").replaceAll("_", " ");
  if (normalized === "layering") {
    return "layering_like";
  }
  if (normalized === "quote stuffing") {
    return "quote_stuffing";
  }
  if (normalized === "liquidity evaporation") {
    return "liquidity_evaporation";
  }
  return "spoofing_like_wall";
}

function calculateRisk(config: {
  cancelStyle: CancelStyle;
  distanceFromMidBps: number;
  lifetimeSeconds: number;
  noiseCover: NoiseCover;
  scenarioType: string;
  wallSizeMultiplier: number;
}) {
  let score = 0.2;
  score += Math.min(config.wallSizeMultiplier / 20, 0.35);
  score += config.lifetimeSeconds <= 5 ? 0.18 : 0.08;
  score += config.distanceFromMidBps <= 15 ? 0.16 : config.distanceFromMidBps <= 30 ? 0.08 : 0.02;
  score += config.cancelStyle === "instant" ? 0.14 : config.cancelStyle === "partial" ? 0.08 : 0.04;
  score += config.noiseCover === "none" ? 0.1 : config.noiseCover === "low" ? 0.04 : -0.04;
  score += config.scenarioType === "quote stuffing" ? 0.12 : 0;

  const boundedScore = Math.max(0.05, Math.min(0.99, score));
  const label = boundedScore >= 0.78 ? "High" : boundedScore >= 0.52 ? "Medium" : "Low";

  return {
    explanation: `${label} predicted detection risk (${boundedScore.toFixed(2)}). Larger walls, shorter lifetimes, closer placement, and instant cancellation increase detector confidence.`,
    label,
    score: boundedScore
  };
}
