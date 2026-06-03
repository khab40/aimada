import type { DetectorScores } from "@/types/arena";

export function DetectorConfidence({ scores = [] }: { scores?: DetectorScores["scores"] }) {
  return (
    <section>
      <h2>Detector Confidence</h2>
      <ul>
        {scores.map((score) => (
          <li key={score.name}>
            {score.name}: {(score.confidence * 100).toFixed(0)}%
          </li>
        ))}
      </ul>
    </section>
  );
}
