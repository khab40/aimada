# RELEVENCE.md

# AI Market Abuse Detection Arena — Relevance to Nebius Serverless Build Challenge

## 1. Project summary

**AI Market Abuse Detection Arena** is a cloud-native AI laboratory for simulating, detecting, explaining, and replaying financial market-abuse scenarios. The project combines a lightweight limit-order-book simulator, red-team manipulation agents, Detection workflows, AI Investigator explanations, and Managed Experiment jobs.

The core demo story is simple:

1. A synthetic market runs in real time.
2. A red-team agent injects a manipulation attack, for example spoofing or layering.
3. The limit order book reacts: visible liquidity changes, imbalance appears, and price moves.
4. Smart Detection raises an alert.
5. AI Investigator generates an analyst-style explanation and incident report.
6. Managed Experiment jobs run many variants of the attack scenario in parallel.
7. Results, metrics, alerts, and replay artifacts are stored for review and benchmarking.

The project should not be positioned as a production-grade exchange simulator. It should be positioned as a **research-inspired synthetic market-abuse testing platform**.

---

## 2. Why this is relevant to Nebius Serverless

The strongest reason this project fits the Nebius Serverless Build Challenge is that market-abuse experiments are naturally parallel. One simulation run is a small isolated workload; hundreds or thousands of scenario variants can be executed independently.

This makes the project a good fit for serverless execution:

- each simulation run can be packaged as a short job;
- attack scenarios can be generated as independent experiment configurations;
- detector robustness can be evaluated across many market regimes;
- results can be aggregated into precision, recall, false-positive rate, alert delay, attack profit, and market-quality metrics;
- users do not need to manage long-running infrastructure for batch experiments.

A strong Nebius story is:

> Run one market simulation live in the UI. Run 100-1000 attack/detection variants as Managed Experiments on Nebius Serverless Cloud. Use Nebius AI to explain alerts. Store replayable evidence as artifacts.

This is better than using serverless as a decorative backend call. In this project, serverless is the **experiment execution engine**.

---

## 3. Added value of the project

The main added value is not simply “detect spoofing once.” The broader value is that the project creates a scalable synthetic-data and evaluation environment for market surveillance.

### 3.1 Synthetic abuse data generation

Real market-abuse data is difficult to obtain. It is rare, sensitive, confidential, and hard to label. This project can generate labeled synthetic scenarios:

- normal market sessions;
- spoofing attacks;
- layering attacks;
- quote-stuffing attacks;
- momentum-ignition scenarios;
- mixed or subtle manipulation patterns.

This synthetic data can be used for demos, detector testing, training materials, benchmarking, and later ML experiments.

### 3.2 Detector stress-testing

A detector that works on one obvious scenario is not impressive. The added value comes from testing detection logic across many conditions:

- thin liquidity;
- deep liquidity;
- high volatility;
- normal market background;
- news shock;
- obvious attack;
- subtle attack;
- multiple red-team agents;
- different cancellation delays;
- different detector thresholds.

Nebius Serverless makes this scalable. The system becomes a market-surveillance test harness rather than a one-off demo.

### 3.3 Explainable alerts

Smart Detection should produce evidence, while AI Investigator should explain that evidence in natural language. The LLM should not be the core detector. It should be the analyst assistant.

Example explanation:

> Agent R-17 placed a large sell-side order near the best ask. The order represented 42% of visible ask liquidity, was cancelled after 1.8 seconds, and was followed by an opposite-side buy order after the mid-price moved down. This sequence is consistent with spoofing.

This makes the result understandable to judges, analysts, and non-specialist viewers.

### 3.4 Replayable evidence

Each experiment should produce an evidence bundle:

- orders.json;
- trades.json;
- book_snapshots.json;
- alerts.json;
- metrics.json;
- incident_report.md;
- replay.json.

This creates a serious audit and evaluation story. A user can replay the suspicious episode, inspect the book, review the alert, and compare metrics.

---

## 4. Recommended UI and product flow

The project should be shown as a synthetic market arena with a focused Detection workflow.

### Core UI tabs

- **Arena** — live limit order book, market visualization, agents, trades, and alerts.
- **Scenario Generator** — creates concrete attack plans, for example thin-liquidity sell-side spoofing.
- **Detection** — shows detection scores, suspicious agents, evidence, replay, and AI Investigator reports.
- **Experiments** — keeps experiment-oriented workflows discoverable.
- **Nebius AI** — shows model selection, inference, batch execution, GPU utilization, datasets, and Managed Experiments.
- **About** — explains architecture, pipeline, research papers, and benchmark summary.

### Nebius AI

The Nebius AI page should communicate the cloud-native story clearly. It should include:

1. Cloud Runtime Status
2. Nebius AI inference
3. Attack Scenario Generator integration
4. Managed Experiment runner
5. Scenario Batch Generator
6. Experiment Artifacts / Replay Storage
7. Usage & Cost Monitor
8. Deployment Health

The strongest demo flow is:

1. Start normal market.
2. Generate and inject spoofing attack.
3. Detector raises alert.
4. Click **Explain Current Alert**.
5. Nebius AI generates explanation.
6. Click **Run 100 Variants on Nebius Serverless**.
7. Show detection performance metrics.
8. Click **Save Evidence Bundle**.
9. Show replay, metrics, alerts, and report artifacts.

---

## 5. Why the project can be interesting for judges

The project has several qualities that are useful in a build challenge:

- it is visual: order book, price movement, attack timeline, alerts, red/blue scores;
- it has a real domain: market abuse surveillance, synthetic data, financial compliance;
- it uses serverless for a natural parallel workload;
- it uses AI for useful explanation and scenario generation, not just chatbot decoration;
- it produces measurable outputs;
- it has a strong demo narrative.

The best short positioning is:

> AI Market Abuse Detection Arena is a cloud-native AI laboratory for generating, detecting, explaining, and replaying market-abuse scenarios at scale.

The practical punchline is:

> Instead of testing surveillance logic on rare and sensitive real abuse cases, we generate labeled synthetic abuse scenarios at scale and evaluate detector robustness using Nebius Serverless.

---

## 6. Criticism and risks

### 6.1 Risk: the simulator may look too simplified

A real exchange simulator is complex. It includes queue priority, realistic latency, partial fills, hidden liquidity, multiple order types, and many market participants. A simple implementation may be criticized as a toy.

Mitigation: be honest and call it **ABIDES-lite** or **research-inspired LOB simulation**. Focus the value proposition on scenario generation, detector testing, replay, and cloud-scale experiments — not on full market realism.

### 6.2 Risk: detector validation may look circular

If the project generates attacks and then uses handcrafted rules to detect exactly those attacks, the detector may look weak.

Mitigation: include normal baseline scenarios, false-positive measurement, stealth levels, and multiple market regimes. Show metrics such as precision, recall, false-positive rate, and alert delay.

### 6.3 Risk: LLM use may look unreliable

LLMs should not be used as the primary market-abuse detector. That would be hard to defend.

Mitigation: use deterministic or statistical evidence extraction first. Then use Nebius AI for AI Investigator reports, attack-plan generation, and analyst assistance.

### 6.4 Risk: mocked Nebius integration weakens the challenge fit

If Nebius AI is mostly mock data, the project may feel superficial.

Mitigation: implement at least one real end-to-end Nebius path:

1. submit batch simulation job;
2. run N simulations;
3. return metrics;
4. store or display artifacts;
5. optionally call an AI endpoint for explanation.

One real serverless workflow is more valuable than many mocked panels.

### 6.5 Risk: scope explosion

The project can become too large: simulator, matching engine, agents, attacks, detectors, LLMs, serverless jobs, storage, replay, charts, and reports.

Mitigation: keep MVP narrow:

- one abuse type: spoofing;
- one detector: rule-based spoofing score;
- one attack generator;
- one live simulation;
- one Nebius Serverless batch runner;
- one AI explanation button;
- one replay/evidence format;
- polished UI.

---

## 7. MVP recommendation

For the Build Challenge, the most credible MVP is:

1. **Spoofing attack generator** — creates a structured attack plan.
2. **LOB simulator** — runs a simplified market with honest agents and one red-team spoofer.
3. **Smart Detection** — calculates spoofing risk score using large-order, fast-cancel, imbalance-flip, and price-impact signals.
4. **AI Investigator** — converts detector evidence into an analyst-style report.
5. **Managed Experiment runner** — runs many attack variants in parallel and aggregates metrics.
6. **Replayable artifacts** — stores orders, trades, alerts, metrics, and incident report.
7. **Mission-control UI** — shows live attack, detection, Nebius batch jobs, and evidence bundle.

This scope is narrow enough to build, but strong enough to be credible.

---

## 8. Final value statement

**AI Market Abuse Detection Arena** is valuable because it turns market-abuse surveillance from a static demo into a scalable AI-driven experimentation lab. It lets users generate manipulation scenarios, simulate market impact, detect suspicious behavior, explain alerts, run many variants on serverless infrastructure, and store replayable evidence.

For Nebius, it demonstrates a serious AI + Serverless use case:

- Nebius Serverless for parallel simulation workloads;
- Nebius AI Endpoints for explanations and reports;
- Nebius storage for replayable artifacts;
- cloud-native experimentation for a real financial-domain problem.

The final message should be:

> Simulate market manipulation. Detect it in real time. Explain it with AI. Scale the experiments with Nebius Serverless. Store the evidence for replay and benchmarking.
