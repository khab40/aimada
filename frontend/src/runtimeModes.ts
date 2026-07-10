export type RuntimeMode = "local-demo" | "hybrid" | "nebius-cloud";
export type RuntimeStatus = "Ready" | "Mock" | "Connected" | "Not configured" | "Endpoint unavailable" | "Error";
export type RuntimeComponent = "Frontend" | "Backend" | "Runner" | "AI Endpoint" | "Jobs" | "Storage";

export const RUNTIME_MODE_KEY = "aimada.runtimeMode";
export const RUNTIME_MODE_EVENT = "aimada-runtime-mode-change";

export const runtimeComponents: RuntimeComponent[] = ["Frontend", "Backend", "Runner", "AI Endpoint", "Jobs", "Storage"];
export const runtimeOptions: { description: string; label: string; marker: string; matrix: Record<RuntimeComponent, RuntimeStatus>; value: RuntimeMode }[] = [
  {
    description: "No credentials required. Mock AI and local demo data stay available.",
    label: "Local Demo",
    matrix: {
      "AI Endpoint": "Mock",
      Backend: "Ready",
      Frontend: "Ready",
      Jobs: "Mock",
      Runner: "Ready",
      Storage: "Mock"
    },
    marker: "🟢",
    value: "local-demo"
  },
  {
    description: "Local UI, backend, and runner with Nebius endpoint and job calls when configured.",
    label: "Hybrid",
    matrix: {
      "AI Endpoint": "Not configured",
      Backend: "Ready",
      Frontend: "Ready",
      Jobs: "Not configured",
      Runner: "Ready",
      Storage: "Mock"
    },
    marker: "🟡",
    value: "hybrid"
  },
  {
    description: "Production-style cloud runtime across app, workers, AI, jobs, and artifacts.",
    label: "Nebius Cloud",
    matrix: {
      "AI Endpoint": "Connected",
      Backend: "Ready",
      Frontend: "Ready",
      Jobs: "Connected",
      Runner: "Connected",
      Storage: "Connected"
    },
    marker: "🟣",
    value: "nebius-cloud"
  }
];
export const visibleRuntimeOptions = runtimeOptions.filter((option) => option.value !== "hybrid");

export function getStoredRuntimeMode(): RuntimeMode {
  const stored = window.localStorage.getItem(RUNTIME_MODE_KEY);
  return stored === "nebius-cloud" ? stored : "local-demo";
}

export function storeRuntimeMode(mode: RuntimeMode) {
  window.localStorage.setItem(RUNTIME_MODE_KEY, mode);
  window.dispatchEvent(new CustomEvent(RUNTIME_MODE_EVENT, { detail: mode }));
}
