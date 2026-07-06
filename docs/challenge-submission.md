# Challenge Submission

AI Market Abuse Detection Arena is a visual, synthetic, serverless learning arena for order-book abuse-like pattern detection and AI-generated incident explanations.

## What It Demonstrates

- A live synthetic exchange with normal and abuse-like trading agents.
- Detector outputs for spoofing-like, layering-like, quote-stuffing-like, and liquidity-shock patterns.
- A React arena UI showing order-book state, charts, agent activity, alerts, and incident details.
- Nebius AI endpoints that explain events, summarize simulations, and generate incident reports.
- AI Detector Tournament using Nebius Serverless Jobs as the batch compute layer.
- A local fallback benchmark path that runs labeled synthetic scenarios and reports precision, recall, F1, false positives, false negatives, and latency.

## Intended Submission Assets

- Demo video showing live scenario launch, alert generation, and explanation flow.
- Screenshots for the arena view, benchmark view, and Incident Details.
- Benchmark report generated from synthetic scenarios.
- Detector tournament artifacts from `POST /api/nebius/tournament/start`, including `metrics.csv`, `results.json`, charts, and `benchmark_report.md`.
- Architecture diagram and deployment notes.

## Evaluation Framing

The project is not a production market surveillance system. It is a synthetic demo and research scaffold for exploring detector behavior, visualization, and AI-assisted explanations.
