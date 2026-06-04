# Design Ideas

## Theme Mode Switcher

Add a compact widget in the top-right corner of the shared UI shell that lets the operator switch between:

- Day mode
- Night mode
- System mode

The control should persist the selected preference locally and apply the theme across the arena, benchmark, lab, and about screens. System mode should follow the operating system `prefers-color-scheme` setting.

## Product Modes

1. Live Arena Mode

A visual, game-like market where red-team and blue-team agents act in real time.

2. Experiment Mode

Batch simulations using Nebius Serverless AI Jobs.

3. Judge Mode

AI explains a selected timeline segment and produces an investigation report.

This gives the project both the visual demo surface and the serious engineering path needed for the challenge.

## 3D Market Battlefield Simulator

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
