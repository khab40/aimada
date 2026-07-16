import { expect, test, type Page, type Route } from "@playwright/test";

type ApiState = {
  experiment?: ReturnType<typeof experimentFixture> | null;
  jobs?: Record<string, unknown>[];
  leaderboard?: Record<string, unknown>[];
  localRun?: (route: Route) => Promise<void>;
  scenarioRequests?: Record<string, unknown>[];
  submitCalls?: number;
  summary?: Record<string, unknown> | null;
};

function experimentFixture(overrides: Record<string, unknown> = {}) {
  return {
    artifact_dir: "/tmp/EXP-SEEDED",
    artifact_paths: {},
    attack_count: 24,
    batch_size: 6,
    created_at: "2026-07-16T10:00:00Z",
    id: "EXP-SEEDED",
    metrics: [],
    name: "Seeded surveillance run",
    nebius_mode: "local_parallel_batch",
    scenarios: ["spoofing_like_wall", "layering_like"],
    seed: 424242,
    status: "manifest_generated",
    updated_at: "2026-07-16T10:00:00Z",
    ...overrides
  };
}

function jobFixture(overrides: Record<string, unknown> = {}) {
  return {
    artifact_paths: {},
    attack_count: 24,
    backend: "local_parallel_batch",
    batch_end: 24,
    batch_start: 0,
    created_at: "2026-07-16T10:01:00Z",
    experiment_id: "EXP-SEEDED",
    job_id: "JOB-LOCAL-1",
    message: "Completed deterministic batch.",
    status: "completed",
    updated_at: "2026-07-16T10:02:00Z",
    ...overrides
  };
}

async function mockApi(page: Page, state: ApiState = {}) {
  state.jobs ??= [];
  state.leaderboard ??= [];
  state.scenarioRequests ??= [];
  state.submitCalls ??= 0;

  await page.route("http://localhost:8000/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    const json = (body: unknown, status = 200) => route.fulfill({
      body: JSON.stringify(body),
      contentType: "application/json",
      status
    });

    if (path === "/api/nebius/status") {
      return json({
        api_key_configured: true,
        checked_at: "2026-07-16T10:00:00Z",
        cli_installed: true,
        endpoint_base_url: "https://mock.nebius.example",
        endpoint_base_url_configured: true,
        endpoint_health: { status: "healthy" },
        endpoint_token_configured: true,
        incident_explainer_configured: true,
        investigation_report_configured: true,
        investigation_team_configured: true,
        job_artifacts_collection_configured: true,
        job_health: { status: "healthy" },
        job_image: "registry.example/lob-arena:test",
        job_logs_template_configured: true,
        job_resource_configured: true,
        job_status_template_configured: true,
        job_submit_template_configured: true,
        market_abuse_scenario_configured: true,
        model: "mock-model",
        orderbook_alert_configured: true,
        runner_health: { status: "healthy" },
        scenario_generator_configured: true,
        storage_health: { status: "healthy" },
        tenant_id_configured: true
      });
    }
    if (path === "/api/nebius/observatory") {
      return json({
        adapter: { mode: "mock", name: "test", replacement_target: "none" },
        benchmark_artifacts: {},
        capabilities: [],
        checked_at: "2026-07-16T10:00:00Z",
        endpoint_base_url_configured: true,
        endpoint_health: { status: "healthy" },
        endpoint_mode: "mock",
        job_health: { status: "healthy" },
        orderbook_alert_configured: true,
        runtime_health: [],
        screenshots: [],
        storage_health: { status: "healthy" },
        usage: {
          endpoint_avg_latency_seconds: 0,
          endpoint_purpose: "test",
          endpoint_requests: 0,
          evidence_status: "mock",
          job_artifacts: [],
          job_output_files: 0,
          job_runtime: "0s",
          job_simulations: 0
        }
      });
    }
    if (path === "/api/nebius/evidence") return json([]);
    if (path === "/api/experiments/reports") return json({ nebius_batches: [] });

    if (path === "/api/nebius/scenario-generator/generate" && method === "POST") {
      const payload = request.postDataJSON() as Record<string, unknown>;
      state.scenarioRequests?.push(payload);
      const seed = Number(payload.seed);
      return json({
        description: `Deterministic scenario generated from seed ${seed}.`,
        difficulty: payload.difficulty,
        duration_ticks: payload.duration_ticks,
        endpoint: "mock",
        events: [{
          agent_id: "ABUSER_SEEDED",
          event_id: `event-${seed}`,
          event_type: "place_order",
          message: "Seeded wall placed",
          scenario_family: payload.manipulation_type,
          scenario_id: `SCN-${seed}`,
          scenario_name: payload.manipulation_type,
          stage: "wall_placed",
          symbol: payload.symbol,
          tick: 12,
          type: "limit_order"
        }],
        expected_detector_behavior: {
          expected_risk_score: 0.91,
          false_positive_risk: "low",
          primary_signals: ["wall_size_ratio"]
        },
        explanation: "Deterministic fixture",
        ground_truth: {
          expected_detector_targets: ["spoofing_like"],
          label: payload.manipulation_type,
          manipulation_windows: [{ end_tick: 30, start_tick: 10 }],
          manipulator_agent_ids: ["ABUSER_SEEDED"],
          positive_event_ids: [`event-${seed}`]
        },
        liquidity_regime: payload.liquidity_regime,
        manipulation_type: payload.manipulation_type,
        mode: "mock",
        replay: { route: "/arena", supported: true },
        scenario_id: `SCN-${seed}`,
        source: { seed },
        symbol: payload.symbol,
        title: `Seeded scenario ${seed}`,
        volatility_regime: payload.volatility_regime
      });
    }

    if (path === "/api/experiments" && method === "GET") {
      return json(state.experiment ? [state.experiment] : []);
    }
    if (path === "/api/experiments" && method === "POST") {
      const payload = request.postDataJSON() as Record<string, unknown>;
      state.experiment = experimentFixture({
        attack_count: payload.attack_count,
        batch_size: payload.batch_size,
        name: payload.name,
        scenarios: payload.scenarios,
        seed: payload.seed,
        status: "draft"
      });
      return json(state.experiment);
    }

    const experimentPath = path.match(/^\/api\/experiments\/([^/]+)(?:\/(.+))?$/);
    if (experimentPath) {
      const action = experimentPath[2];
      if (!action && method === "GET") return json(state.experiment ?? experimentFixture());
      if (action === "jobs" && method === "GET") return json(state.jobs);
      if (action === "summary" && method === "GET") {
        return state.summary ? json(state.summary) : json({ detail: "not aggregated" }, 404);
      }
      if (action === "leaderboard" && method === "GET") return json(state.leaderboard);
      if (action === "investigations" && method === "GET") return json([]);
      if (action === "run-local-batch" && method === "POST") {
        if (state.localRun) return state.localRun(route);
        return json({
          artifact_paths: {},
          batch_size: 6,
          created_at: "2026-07-16T10:02:00Z",
          elapsed_seconds: 1.2,
          experiment_id: "EXP-SEEDED",
          id: "BATCH-1",
          metrics: [],
          mode: "local_parallel_batch",
          runs: 24,
          scenarios: ["spoofing_like_wall"],
          status: "completed"
        });
      }
      if (action === "submit-nebius" && method === "POST") {
        state.submitCalls = (state.submitCalls ?? 0) + 1;
        const submitted = jobFixture({
          backend: "nebius_serverless_job",
          job_id: "JOB-CLOUD-1",
          message: "Submitted to Nebius Cloud.",
          status: "running"
        });
        state.jobs = [submitted];
        return json(submitted);
      }
    }

    return json({ detail: `Unhandled test route: ${method} ${path}` }, 404);
  });
}

async function openWorkflowStep(page: Page, name: string) {
  const tab = page.getByRole("tab", { name: new RegExp(name) });
  await expect(tab).toBeEnabled();
  await tab.click();
}

test("sidebar curtain and Local/Cloud chooser stay usable when expanded and collapsed", async ({ page }) => {
  await mockApi(page);
  await page.setViewportSize({ height: 900, width: 1440 });
  await page.goto("/arena?demo=real");

  const sidebar = page.getByRole("complementary", { name: "Application navigation" });
  const workspace = page.locator(".app-workspace");
  const runtimeButton = page.locator(".runtime-status-pill");
  const expandedSidebar = await sidebar.boundingBox();
  const expandedWorkspace = await workspace.boundingBox();
  expect(expandedSidebar?.height).toBe(900);
  expect(expandedWorkspace!.x).toBeGreaterThanOrEqual(expandedSidebar!.x + expandedSidebar!.width);

  await runtimeButton.click();
  let dialog = page.getByRole("dialog", { name: "Runtime mode selection" });
  await expect(dialog).toBeVisible();
  let dialogBox = await dialog.boundingBox();
  expect(dialogBox!.x).toBeGreaterThanOrEqual(expandedSidebar!.x + expandedSidebar!.width - 1);
  expect(dialogBox!.x + dialogBox!.width).toBeLessThanOrEqual(1440);
  await expect(dialog.getByRole("button", { name: "Local Demo", exact: true })).toHaveAttribute("aria-pressed", "true");

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await page.getByRole("button", { name: "Collapse navigation" }).click();
  const collapsedSidebar = await sidebar.boundingBox();
  expect(collapsedSidebar!.width).toBeLessThanOrEqual(80);

  await runtimeButton.click();
  dialog = page.getByRole("dialog", { name: "Runtime mode selection" });
  dialogBox = await dialog.boundingBox();
  expect(dialogBox!.width).toBeGreaterThan(500);
  expect(dialogBox!.x + dialogBox!.width).toBeLessThanOrEqual(1440);
  await dialog.getByRole("button", { name: "Nebius Cloud", exact: true }).click();
  await expect(runtimeButton).toContainText("Nebius Cloud");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("lob-arena.runtimeMode"))).toBe("nebius-cloud");
});

test("simulation configuration sends the same deterministic request for a fixed seed", async ({ page }) => {
  const state: ApiState = { scenarioRequests: [] };
  await mockApi(page, state);
  await page.goto("/nebius");
  await openWorkflowStep(page, "Scenario Generator");

  await page.getByLabel("Manipulation type").selectOption("layering_like");
  await page.getByLabel("Difficulty").selectOption("hard");
  await page.getByLabel("Symbol").fill("seedx");
  await page.getByLabel("Duration (ticks)").fill("180");
  await page.getByLabel("Liquidity", { exact: true }).selectOption("deep");
  await page.getByLabel("Volatility", { exact: true }).selectOption("low");
  await page.getByLabel("Fixed seed").fill("8675309");

  const generate = page.getByRole("button", { name: "Generate AI Scenario" });
  await generate.click();
  await expect(page.getByText("Seeded scenario 8675309")).toBeVisible();
  await expect(page.getByText("tick 12: Seeded wall placed")).toBeVisible();
  await generate.click();
  await expect.poll(() => state.scenarioRequests?.length).toBe(2);
  expect(state.scenarioRequests?.[0]).toEqual(state.scenarioRequests?.[1]);
  expect(state.scenarioRequests?.[0]).toMatchObject({
    difficulty: "hard",
    duration_ticks: 180,
    liquidity_regime: "deep",
    manipulation_type: "layering_like",
    seed: 8675309,
    symbol: "SEEDX",
    volatility_regime: "low"
  });
});

test("serverless run submission enters a visible in-progress state", async ({ page }) => {
  const state: ApiState = { experiment: experimentFixture() };
  await mockApi(page, state);
  await page.goto("/nebius");

  await page.locator(".runtime-status-pill").click();
  await page.getByRole("dialog", { name: "Runtime mode selection" })
    .getByRole("button", { name: "Nebius Cloud", exact: true })
    .click();
  await openWorkflowStep(page, "Detector Tournament");
  const submit = page.getByRole("button", { name: "Run serverless job", exact: true });
  await expect(submit).toBeEnabled();
  await submit.click();

  await expect.poll(() => state.submitCalls).toBe(1);
  await expect(page.getByText("pending cloud job execution: Submitted to Nebius Cloud.")).toBeVisible();
  await expect(page.getByRole("cell", { name: "JOB-CLOUD-1" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "running" })).toBeVisible();
  await expect(submit).toBeDisabled();
});

test("local run exposes progress and recovers from an API error", async ({ page }) => {
  let releaseRun: (() => void) | undefined;
  const state: ApiState = {
    experiment: experimentFixture(),
    localRun: async (route) => {
      await new Promise<void>((resolve) => {
        releaseRun = resolve;
      });
      await route.fulfill({
        body: JSON.stringify({ detail: "worker capacity exhausted" }),
        contentType: "application/json",
        status: 503
      });
    }
  };
  await mockApi(page, state);
  await page.goto("/nebius");
  await openWorkflowStep(page, "Detector Tournament");

  const run = page.getByRole("button", { name: "Run Local Demo tournament" });
  await run.click();
  await expect(page.getByText(/Running the tournament in an isolated/)).toBeVisible();
  await expect(run).toBeDisabled();
  await expect.poll(() => Boolean(releaseRun)).toBe(true);
  releaseRun?.();

  await expect(page.getByText("Run experiment local batch failed: 503")).toBeVisible();
  await expect(run).toBeEnabled();
});

test("completed results render status, alert, failure, and detector metrics", async ({ page }) => {
  const state: ApiState = {
    experiment: experimentFixture({
      artifact_paths: { alerts: "/tmp/alerts.json", detector_metrics: "/tmp/metrics.json" },
      status: "completed"
    }),
    jobs: [jobFixture()],
    leaderboard: [{
      alert_count: 37,
      avg_detection_latency_ms: 18,
      detector: "spoofing_like_detector",
      f1: 0.912,
      model: "rules_v2",
      precision: 0.934,
      recall: 0.891,
      scenario: "spoofing_like_wall"
    }],
    summary: {
      artifact_paths: { detector_metrics: "/tmp/metrics.json" },
      experiment_id: "EXP-SEEDED",
      f1_by_scenario: { spoofing_like_wall: 0.912 },
      failed_runs: 2,
      investigation_count: 4,
      precision_by_scenario: { spoofing_like_wall: 0.934 },
      recall_by_scenario: { spoofing_like_wall: 0.891 },
      scenarios: ["spoofing_like_wall"],
      total_alerts: 37,
      total_attacks: 24
    }
  };
  await mockApi(page, state);
  await page.goto("/nebius");
  await openWorkflowStep(page, "Detector Tournament");

  const lab = page.locator(".experiment-lab-panel");
  await expect(lab.locator(".runtime-metric").filter({ hasText: "Status" })).toContainText("completed");
  await expect(lab.locator(".runtime-metric").filter({ hasText: "Jobs" })).toContainText("1/1 done");
  await expect(lab.locator(".runtime-metric").filter({ hasText: "Alerts" })).toContainText("37");
  await expect(lab.locator(".runtime-metric").filter({ hasText: "Failed runs" })).toContainText("2");
  await expect(lab.locator(".runtime-metric").filter({ hasText: "Seed" })).toContainText("424242");
  await expect(page.getByRole("cell", { name: "spoofing like detector" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "0.912" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "18 ms" })).toBeVisible();
});

test("attack tracker and market timeline visualize attack events", async ({ page }) => {
  await mockApi(page);
  await page.goto("/arena?demo=real");

  await expect(page.getByRole("heading", { name: "Attack Tracker" })).toBeVisible();
  await expect(page.locator(".attack-stage.active")).toContainText("Armed");
  await page.getByRole("button", { name: "Market Timeline" }).click();
  const markers = page.getByLabel("Timeline attack markers");
  await expect(markers).toContainText("attack started");
  await expect(markers).toContainText("detector warning");
  await expect(markers).toContainText("T0");
  await expect(page.getByRole("img", { name: "Mid price, spread bps, and imbalance timeline" })).toBeVisible();
  await expect(markers).toContainText("incident confirmed", { timeout: 7_000 });
});
