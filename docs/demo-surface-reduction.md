# Demo Surface Reduction

AIMADA is now positioned as a Nebius AI Serverless-powered market surveillance command center. The default product surface prioritizes the AI Command Center, with the Arena serving as a Market Workload Generator.

## Default Demo Flow

1. Generate or select a suspicious market scenario.
2. Replay it in the Arena / Market Workload Generator.
3. Create detector output and an incident.
4. Send the incident to Nebius AI Serverless.
5. Show the AI investigation and report output.
6. Optionally run an AI Detector Tournament.

## Default Navigation

- AI Command Center
- Arena / Workload Generator
- Docs / Demo

Secondary pages and advanced setup remain in the codebase but are not prominent in the default demo.

## Feature Flags

Backend flags:

```bash
ENABLE_GOOGLE_AUTH=false
ENABLE_ADVANCED_ATTACK_CONTROLS=false
ENABLE_LEGACY_PAGES=false
```

Frontend flags:

```bash
VITE_ENABLE_GOOGLE_AUTH=false
VITE_ENABLE_ADVANCED_ATTACK_CONTROLS=false
VITE_ENABLE_LEGACY_PAGES=false
```

Google auth is hidden unless explicitly enabled. The local demo does not require authentication. Advanced attack controls and legacy navigation are available for development or review, but hidden by default for demo clarity.
