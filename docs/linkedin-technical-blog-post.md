# LinkedIn Technical Blog Post

Repository: https://github.com/khab40/ai-market-abuse-detection-arena

Hashtag: #NebiusServerlessChallenge

## Post

I built AI Market Abuse Detection Arena for the #NebiusServerlessChallenge: a synthetic, serverless-oriented market simulation that makes order-book abuse-like patterns visible, testable, and explainable without using real trading data.

Repository: https://github.com/khab40/ai-market-abuse-detection-arena

The problem I wanted to explore is a common one in technical AI demos: the interesting part of the domain is hard to show safely. Market surveillance involves sensitive data, specialized microstructure concepts, noisy event streams, and a lot of language that can become misleading if the system is presented as a real compliance tool. I did not want to build a product that claims to detect real manipulation. Instead, I built an educational arena where synthetic normal agents and synthetic abuse-like agents interact inside a controlled limit-order-book simulation. That gives the project a concrete engineering surface: generate market events, inject labeled scenarios, run deterministic detectors, preserve evidence, and use AI to explain what the detector already found.

The architecture has two main paths.

The first is the interactive path. A React and Vite frontend renders the live arena: order-book ladders, price and spread charts, liquidity heatmaps, agent activity, detector confidence, incident cards, and replay/report views. A FastAPI backend owns the control plane. The browser sends live commands over WebSocket, the backend runs the simulation, and the UI receives complete `arena_state` messages. This keeps the browser away from both the simulation internals and the Nebius endpoint credentials.

Inside the backend, the core loop is intentionally deterministic. A synthetic exchange, order book, and matching engine process actions from normal market-making, liquidity-taking, and noise agents. Scenario agents can then inject bounded spoofing-like, layering-like, quote-stuffing-like, liquidity-evaporation, or pump-and-cancel style behavior. The key word is "bounded": these are synthetic patterns for education and detector testing, not instructions for real market activity.

The second path is the batch benchmark path. This is where Nebius Serverless AI Jobs fit naturally. Instead of asking a live UI to run dozens or hundreds of simulations, the job path can run repeatable detector tournaments offline, generate synthetic datasets, extract features, and write benchmark artifacts. The benchmark outputs are designed to be reviewable: JSON results, CSV metrics, Markdown reports, and chart-ready data. The metric vocabulary is simple but useful: precision, recall, F1, false positives, false negatives, and detection latency against known synthetic scenario labels.

Nebius Serverless AI Endpoints play a different role. They do not make the original detection decision. The deterministic detector produces structured evidence first: spread, depth, imbalance, message rate, cancel-to-trade ratio, wall size ratio, order lifetime, confidence scores, and scenario labels. The backend then sends a compact incident payload to the endpoint. The endpoint returns a readable explanation, recommended review actions, or a bounded synthetic scenario draft. This split matters because it keeps the system auditable. AI is used for explanation and narration; evidence remains structured and reproducible.

Implementation-wise, the repo is organized into five main areas:

`backend/` contains the FastAPI app, simulation engine, exchange model, detectors, incident storage, Nebius client, and report generation.

`frontend/` contains the React arena, Demo page, Detection workflow, Scenario Generator, Nebius AI page, and reusable visualization components.

`serverless/` contains the Nebius endpoint app, job runners, Dockerfiles, and example configs for endpoint and batch execution.

`docs/` captures architecture records, deployment notes, runtime model, benchmark methodology, safety framing, and challenge submission notes.

`outputs/` stores generated artifacts such as events, incidents, labels, explanations, and benchmark reports.

The most important design choice was separating "detect" from "explain." In many AI prototypes, the model is asked to be both the judge and the storyteller. That is convenient, but hard to test. In this project, detectors are deterministic functions over synthetic order-book state. They create incidents with evidence. The AI layer can then translate that evidence into plain English for a reviewer, but it does not silently replace the detector logic.

The current smoke benchmark demonstrates that the pipeline is wired end to end. In the checked-in serverless deployment test artifact, a one-run detector tournament covered spoofing-like and quote-stuffing scenarios. The matching detectors reached precision 1.0, recall 1.0, and F1 1.0 on those synthetic labels, with an average detection latency of 1,500 ms. Non-matching detectors stayed at 0.0 for those scenario-detector pairs. That is not a claim about real market surveillance performance. It is a reproducibility signal: labels, detectors, metrics, and reports are flowing through the same artifact path that a larger benchmark would use.

The broader result is a working research scaffold. A reviewer can start the local stack with Docker Compose, launch a live market arena, inject synthetic scenarios, inspect detector evidence, request AI explanations, and review persisted artifacts. A practitioner can also follow the Nebius deployment notes to split the system into an interactive AI endpoint and offline serverless jobs.

What I like about this project is that it treats AI infrastructure as part of an engineering workflow, not just a chatbot wrapper. Nebius serverless endpoints are useful for low-latency explanation and investigation flows. Nebius serverless jobs are useful for repeatable evaluation work. The frontend makes the domain visible. The backend keeps control of state, credentials, and evidence. The benchmark path makes results measurable.

There are still clear next steps: run a larger archived benchmark, capture real Nebius logs and metrics screenshots, add more scenario families, improve calibration against historical distributions, and build richer replay tools for incident review. But the core idea is already useful: if a domain is high-risk, sensitive, or hard to demonstrate directly, build a synthetic digital twin first. Then make the simulation observable, benchmarkable, and explainable before making stronger claims.

Again, this project is educational. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. It is a technical arena for exploring synthetic order-book behavior, deterministic detector design, serverless AI explanation, and benchmarkable evaluation.

#NebiusServerlessChallenge
