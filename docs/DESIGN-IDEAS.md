# Design Ideas

## Theme Mode Switcher

Status: `[done]`

The shared UI shell includes a compact day/night/system theme selector in the sidebar controls. The selected preference is persisted locally as `aimada.themePreference`, applied through the document `data-theme` attribute, and updated when system mode follows `prefers-color-scheme`. The theme layer now covers shared panels, widget cards, status chips, order-book levels, timeline charts, Recharts tooltips, and the canvas Liquidity Map so Arena, Scenario Generator, Detection, Experiments, Nebius AI, and About screens use a coherent day/night visual language.

Follow-up polish:

- Add an accessibility contrast pass once the final screenshot set is ready.

## Professional Shell And Auth Widget

Status: `[done]`

The shell now treats authentication and display preferences like professional product chrome rather than permanent marketing content. The Google/auth panel can collapse to a compact account control, the vertical navigation toggle is smaller and closer to browser vertical-tab controls, and the product subtitle has been removed from the shell.

The Liquidity Map is also gated by simulation tick progression, so it does not animate or append frames while the arena is paused or has not started from the UI.

## Product Modes

Status: `[partial]`

1. Live Arena Mode

A visual, game-like market where red-team and blue-team agents act in real time.

Implementation: `[done]` through the main Arena, scenario controls, detector panels, incident views, and WebSocket state path.

2. Experiment Mode

Batch simulations using Nebius Serverless AI Jobs.

Implementation: `[done]` through local and production Job paths, the Phase 4.5 Managed Experiment manager, S3 artifact collection, backend synchronization, Detection output integration, and the committed [benchmark evidence bundle](../outputs/benchmark/EXP-18E88EAF/README.md).

Phase 4.5 adds `POST/GET/DELETE /api/experiments` as the durable experiment intent layer. It persists manifests, generates deterministic attack rows, runs or submits batches, normalizes local or S3-synchronized Job artifacts, aggregates metrics, and writes bounded AI Investigator reports. `backend/app/experiments/nebius_orchestrator.py` owns production submit/status/log/artifact collection; missing cloud configuration remains explicit as `real_nebius_pending` rather than simulated success.

Detection outputs make the experiment artifact story visible as a review workflow: experiment list, selected summary, leaderboard, `benchmark_report.md` preview, AI Investigator report links, `artifact_index.json` preview, canonical artifacts, and the original local-batch files. The UI labels this as synthetic educational benchmark evidence and does not present it as real surveillance or compliance output.

3. Judge Mode

AI explains a selected timeline segment and produces an investigation report.

Implementation: `[done]` for incident-centered investigation and report flows.

This gives the project both the visual demo surface and the serious engineering path needed for the challenge.

## Exchange Liquidity Invariant

Status: `[done]`

Maintain a stable two-sided synthetic market while many local, remote, heavy, and LangGraph agents act concurrently. Runtime agent quotes are additive per agent at a shared price level, bounded by a backend quote-size cap, and protected by a baseline ladder guard that restores configured bid/ask depth after each tick.

Future design work:

- Add an optional dedicated Judge Mode timeline-window selector with bounded evidence bundling.

- Add a UI control for baseline ladder levels, base size, and quote cap.
- Add a drifting reference-price model for market regimes where the mid should move materially.
- Add per-agent inventory and risk budgets so richer strategies can quote based on exposure.

## 3D Market Battlefield Simulator

Status: `[partial]`

Create an optional visual simulator that renders the live limit order book as terrain.

Core idea:

- X-axis: price levels around mid-price.
- Y-axis: simulation ticks / time.
- Z-axis: visible liquidity volume.
- Color / heat: imbalance, anomaly pressure, or detector confidence.

In this model, normal liquidity appears as stable terrain ridges. Spoofing-like or layering-like behavior appears as sudden tall walls that form away from the mid-price valley and disappear quickly. A blue-team scanner overlay can show deterministic detector observation, while red-team markers show synthetic scenario agents.

Possible product shape:

- Main widget: 3D order-book canyon with bid and ask terrain on opposite sides of the mid-price valley.
- Side panel: red-team actions, blue-team detections, spoofing probability, and evidence summary.
- Bottom panel: replay timeline with attack start, cancellation, price move, and detection markers.
- Toggle: 3D terrain view vs flat heatmap view.

Current prototype status:

- The concept is captured in `docs/3d-concept-lob.md`.
- A detached frontend prototype exists under `frontend/src/tabs/MarketBattlefield3D/`.
- The prototype adapts the same arena exchange ticker, order book, detector scores, incidents, and agent events into battlefield frames.
- It is intentionally detached from the main navigation until the core Arena and Lab flows are stable enough to support it as a polished demo surface.


## ABIDES inspired
ABIDES is an excellent foundation, but it predates the current generation of AI systems. For LOB Arena, I would extend it with:

1. LLM agents that choose manipulation strategies and explain decisions.
2. RL attackers that learn spoofing and layering policies.
3. Graph neural networks to detect coordinated manipulation across traders.
4. Streaming detection pipelines that score suspicious behavior in real time.
5. Market abuse scoring based on behavioral sequences rather than isolated events.
6. Agent memory and adaptation, allowing attackers and defenders to evolve over multiple episodes.

That would transform ABIDES from a market simulator into a complete AI-vs-AI Market Abuse Arena, closely aligned with the goals of your Nebius Serverless project.
