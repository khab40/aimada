const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

export async function launchScenario(name: string): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/simulation/scenario/${name}`, {
    method: "POST"
  });
  return response.json();
}

export async function getBenchmarkSummary(): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/benchmark/summary`);
  return response.json();
}
