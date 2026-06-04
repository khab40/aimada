Core concept:

3D Market Heatmap = Limit Order Book as terrain

Imagine a 3D surface where:

* X-axis = price levels around mid-price
* Y-axis = time / simulation ticks
* Z-axis / height = liquidity volume at each price level
* Color / heat = pressure or abnormality:
    * blue/green = normal liquidity
    * yellow/orange = growing imbalance
    * red = suspicious / spoofing / manipulation pressure
    * purple/black = detected attack zone

So the order book becomes a mountain landscape. Real liquidity looks like stable ridges. Spoofing looks like a sudden tall wall appearing far from mid-price and disappearing quickly.

For the Nebius demo, it could be called:

“Market Abuse Battlefield”

Visual elements:

1. 3D order book canyon
    * Bid side and ask side are two opposing terrains.
    * Mid-price is the valley center.
    * Large spoof orders appear as temporary “walls.”
2. Attack overlay
    * Red translucent zones show where the red-team agent is manipulating.
    * Blue scanning beam shows the blue-team detector observing suspicious behavior.
3. Agent markers
    * Normal traders: small moving dots.
    * Spoofing agent: red drone/marker.
    * Detector agent: blue radar/observer.
4. Heatmap mode
    * Flat top-down heatmap toggle.
    * Useful for quickly seeing liquidity intensity over time.
5. Replay timeline
    * User can scrub simulation ticks.
    * See how attack forms, influences price, then disappears.
6. Risk score panel
    * “Spoofing probability: 87%”
    * “Order-to-trade ratio spike”
    * “Cancellation burst”
    * “Liquidity wall disappeared”
    * “Price moved after fake depth”

The most attractive version is probably:

Main screen: 3D LOB terrain + real-time agent battle overlay
Side panel: Red Team actions vs Blue Team detections
Bottom panel: timeline with attack events

This is much more original than a normal trading chart because it visually turns market abuse into a real-time strategy game / cyber-defense arena, where liquidity is terrain and agents fight over market microstructure.

New tab: 3D Market Battlefield

Purpose: visual demo of the order book as a live 3D heatmap / terrain, showing spoofing attacks and blue-team detection.

What it shows

Main widget:

3D Limit Order Book terrain

* X-axis: price levels
* Y-axis: simulation ticks / time
* Z-axis: liquidity volume
* Color: risk / imbalance / anomaly score

Extra overlays:

* red “liquidity walls” = suspected spoof orders
* blue scanner/radar = detection agent
* moving dots = trader agents
* vertical event markers = attack start / cancellation / detection
* side panel = explanation of what happened

Example:

“Red agent placed 40,000 fake sell volume 8 ticks above mid-price. Price moved down. Orders cancelled after 3 ticks. Blue agent detected spoofing probability 91%.”

⸻

Suggested module structure

Add a new frontend module:

frontend/
  src/
    tabs/
      MarketBattlefield3D/
        MarketBattlefield3DPage.tsx
        components/
          OrderBookTerrain.tsx
          AgentOverlay.tsx
          AttackMarkers.tsx
          SimulationTimeline.tsx
          DetectionPanel.tsx
          ControlsPanel.tsx
        hooks/
          useMarketBattlefieldData.ts
        types.ts
        mockData.ts



backend/
  src/
    market-battlefield/
      battlefield.controller.ts
      battlefield.service.ts
      battlefield.types.ts
      battlefield.mock.ts

shared/
  types/
    battlefield.ts

npm install three @react-three/fiber @react-three/drei

npm install maath zustand

Use:

* three for 3D rendering
* @react-three/fiber for React integration
* @react-three/drei for camera controls, grid, helpers

Each cell: 
{
  tick: number;
  priceLevel: number;
  side: "bid" | "ask";
  volume: number;
  anomalyScore: number;
}

Data contract
export type BattlefieldCell = {
  tick: number;
  priceLevel: number;
  side: "bid" | "ask";
  volume: number;
  anomalyScore: number;
};

export type BattlefieldEvent = {
  tick: number;
  type: "SPOOF_ORDER" | "CANCEL_BURST" | "PRICE_MOVE" | "DETECTION";
  agentId: string;
  severity: number;
  description: string;
};

export type BattlefieldFrame = {
  tick: number;
  midPrice: number;
  cells: BattlefieldCell[];
  events: BattlefieldEvent[];
  spoofingProbability: number;
};

MarketBattlefield3DPage

Contains:

1. 3D terrain using generated mock order book data
2. Play / pause button
3. Tick slider
4. Spoofing probability panel
5. Event log panel

simulation snapshot -> BattlefieldFrame

later: 
mockData.ts -> 3D widget
REST endpoint /api/battlefield/scenario/:id
real red-agent / blue-agent events
Nebius Serverless detector generates anomaly scores in real time

