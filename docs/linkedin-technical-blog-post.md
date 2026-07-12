# Building AIMADA: An Adversarial Market-Abuse Evaluation Arena with Nebius Serverless AI

I built AIMADA for the #NebiusServerlessChallenge: a synthetic market-abuse simulation and evaluation platform built and validated using Nebius Serverless AI Jobs and Serverless AI Endpoints.

Repository: [https://github.com/khab40/ai-market-abuse-detection-arena](https://github.com/khab40/ai-market-abuse-detection-arena)

The problem I wanted to explore is common in technical AI demos: the interesting part of the domain is hard to show safely. Market surveillance involves sensitive data, specialized microstructure concepts, noisy event streams, and language that can become misleading if a system is presented as a real compliance tool.

I did not want to build a product that claims to detect real manipulation. Instead, I built an educational arena where synthetic normal agents and synthetic abuse-like agents interact inside a controlled limit-order-book simulation. That gives the project a concrete engineering surface: generate market events, inject labeled scenarios, run deterministic detectors, preserve evidence, and use AI to explain what the detector already found.

The architecture has two main paths.

AIMADA was also validated on real Nebius production infrastructure. More than ten Nebius Serverless AI Job runs completed successfully, with successful execution visible in the Nebius production logs. I deployed a Nebius Serverless AI Endpoint with vLLM and successfully exercised multiple routes, including scenario generation, incident analysis, investigation reporting, and structured market-event explanation. Together, these runs produced job artifacts, detector metrics, reports, logs, and endpoint responses. This production validation complements the small checked-in smoke example described below; it does not turn the project into a real-market surveillance claim.

The first path is interactive. A React and Vite frontend renders the live arena: order-book ladders, price and spread charts, liquidity heatmaps, agent activity, detector confidence, incident cards, and replay and report views.

A FastAPI backend owns the control plane. The browser sends live commands over WebSocket, the backend runs the simulation, and the UI receives complete `arena_state` messages. This keeps the browser away from both simulation internals and Nebius endpoint credentials.

### Agents workspace during interactive runs

During an interactive run, AIMADA uses the separate `agent-runner/` agents workspace to generate normal synthetic market activity. At each simulation tick, the backend sends a read-only order-book snapshot to the workspace through its `/decide` API. The workspace returns typed `AgentIntent` objects rather than mutating the market directly. The backend validates and deterministically sorts those intents, remains the single authoritative writer, and applies accepted actions to the synthetic exchange and matching engine.

The workspace runs multiple kinds of trading agents. Top-of-book market makers refresh visible liquidity on both bid and ask sides. Deterministic noise traders make small, cadence-based changes at selected price levels. Periodic liquidity takers alternate bounded synthetic market buys and sells. Optional LangGraph agents use strategies such as liquidity rebalancing, choosing which side to quote from observed depth imbalance. Optional CPU-heavy agents exercise a more computationally expensive decision path for workload testing.

This separation lets the interactive frontend display agent activity while the backend preserves ordering, timeouts, validation, and reproducibility. None of these agents connects to a broker, exchange, or real market. They trade only inside AIMADA’s synthetic order book and cannot emit real trading signals or orders.

Inside the backend, the core loop is intentionally deterministic. A synthetic exchange, order book, and matching engine process actions from normal market-making, liquidity-taking, and noise agents. Scenario agents can then inject bounded spoofing-like, layering-like, quote-stuffing-like, liquidity-evaporation, or pump-and-cancel style behavior.

The key word is “bounded.” These are synthetic patterns for education and detector testing, not instructions for real market activity. AIMADA uses no real trading data and produces no trading signals.

The second path is the batch benchmark path. This is where Nebius Serverless AI Jobs fit naturally. Instead of asking a live UI to run dozens or hundreds of simulations, the job path runs repeatable detector tournaments offline, generates synthetic datasets, extracts features, and writes benchmark artifacts.

The outputs are designed to be reviewable: JSON results, CSV metrics, Markdown reports, logs, and chart-ready data. The metric vocabulary is simple but useful: precision, recall, F1, false positives, false negatives, and detection latency against known synthetic scenario labels.

Nebius Serverless AI Endpoints play a different role. They do not make the original detection decision. A deterministic detector produces structured evidence first: spread, depth, imbalance, message rate, cancel-to-trade ratio, wall size ratio, order lifetime, confidence scores, and scenario labels.

The backend then sends a compact incident payload to the endpoint. The endpoint returns a readable explanation, recommended review actions, investigation assistance, or a bounded synthetic scenario draft. This split matters because it keeps the system auditable. AI is used for explanation, narration, investigation assistance, and bounded scenario generation; evidence remains structured and reproducible.

Implementation-wise, the repository is organized into six main areas.

`backend/` contains the FastAPI application, simulation engine, exchange model, detectors, incident storage, Nebius client, and report generation.

`agent-runner/` contains the agents workspace service, its `/health`, `/agents`, and `/decide` API contracts, the normal synthetic agents, optional CPU-heavy agents, and bounded LangGraph strategies used by the interactive path.

`frontend/` contains the React arena, Demo page, Detection workflow, Scenario Generator, Nebius AI page, and reusable visualization components.

`serverless/` contains the Nebius endpoint application, job runners, Dockerfiles, and example configurations for endpoint and batch execution.

`docs/` captures architecture records, deployment notes, the runtime model, benchmark methodology, safety framing, and challenge submission evidence.

`outputs/` stores generated artifacts such as events, incidents, labels, explanations, metrics, and benchmark reports.

The most important design choice was separating “detect” from “explain.” In many AI prototypes, the model is asked to be both judge and storyteller. That is convenient, but difficult to test.

In AIMADA, detectors are deterministic functions over synthetic order-book state. They create incidents with explicit evidence. The AI layer translates that evidence into plain English for a reviewer, helps organize an investigation, narrates the result, or generates a bounded scenario. It does not silently replace the detector logic or become the source of ground truth.

## Results and reproducibility

The main production result is validation of the complete batch workflow across more than ten successful Nebius Serverless AI Job runs. Those runs exercised container execution, synthetic scenario generation, detector evaluation, metric aggregation, report generation, logging, and artifact persistence on production infrastructure.

The successful runs demonstrate that the batch contract operates beyond a local mock: a job can start from the packaged container, execute the synthetic workload, evaluate detector output against labels, aggregate results, persist artifacts, and expose enough logs for execution review. The deployed Serverless AI Endpoint separately validated the interactive AI contract across scenario generation, incident analysis, investigation reporting, and structured market-event explanation routes.

The checked-in one-run smoke benchmark serves a narrower purpose. It is a small deterministic reproducibility and integration example that another practitioner can execute quickly. In that smoke benchmark, a one-run detector tournament covers spoofing-like and quote-stuffing scenarios. The matching detectors reach precision 1.0, recall 1.0, and F1 1.0 on those deliberately simple synthetic labels, with an average detection latency of 1,500 ms. Non-matching detectors remain at 0.0 for those scenario-detector pairs.

Those values validate the integration, label flow, detector routing, metric calculation, and artifact pipeline. They are not evidence of real-world market-surveillance accuracy, robustness, or compliance suitability. The smoke benchmark is intentionally small enough to reproduce quickly; it is not presented as the project’s main production benchmark.

The broader result is a working research scaffold. A reviewer can start the local stack with Docker Compose, launch a live synthetic market arena, inject bounded scenarios, inspect detector evidence, request AI explanations, and review persisted artifacts. A practitioner can also follow the Nebius deployment notes to separate the interactive endpoint from offline Serverless AI Jobs.

What I like about this project is that it treats AI infrastructure as part of an engineering workflow, not as a chatbot wrapper. Nebius Serverless AI Endpoints support interactive explanation and investigation flows. Nebius Serverless AI Jobs support repeatable evaluation work. The frontend makes the synthetic domain visible, the backend keeps control of state and evidence, and the batch path makes the evaluation inspectable.

The next research steps are to increase benchmark and scenario diversity, develop adaptive adversarial agents, and measure detector degradation as market regimes change. I also want to calibrate synthetic behavior using publicly available market distributions, build richer incident replay tools, and compare deterministic and learned detectors under the same ground-truth labels and evaluation contracts.

That comparison is important. A learned detector should not receive a more forgiving evaluation path simply because its internals are more complex. Deterministic and learned approaches should consume compatible synthetic evidence, preserve the same labels, report the same metric families, and produce artifacts that can be inspected by another practitioner.

Again, AIMADA is synthetic and educational. It uses no real trading data, does not detect real market manipulation, does not provide trading signals, and is not suitable for compliance decisions. It is a technical arena for exploring synthetic order-book behavior, deterministic detector design, serverless AI explanation, and benchmarkable adversarial evaluation.

Repository: [https://github.com/khab40/ai-market-abuse-detection-arena](https://github.com/khab40/ai-market-abuse-detection-arena)

#NebiusServerlessChallenge
