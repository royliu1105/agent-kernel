import { expect, test } from "@playwright/test";

const agentId = "11111111-1111-4111-8111-111111111111";
const kbId = "33333333-3333-4333-8333-333333333333";
const runId = "22222222-2222-4222-8222-222222222222";

test("live Workbench sign-in and core flow sections are available", async ({ page }) => {
  await page.route("**/api/agent-kernel/health", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { state: "online", baseUrl: "http://api:8000" },
    });
  });
  await page.route("**/api/agent-kernel/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        authenticated: false,
        principal_id: null,
        display_name: null,
        workspace_id: null,
        role: null,
        permissions: [],
      },
    });
  });
  await page.route("**/api/agent-kernel/agents", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [{ id: agentId, name: "Ops Agent", status: "active", created_at: "2026-08-04T00:00:00Z" }],
    });
  });
  await page.route("**/api/agent-kernel/knowledge-bases", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          id: kbId,
          name: "Live Operations KB",
          description: null,
          status: "active",
          metadata: {},
          created_at: "2026-08-04T00:00:00Z",
          updated_at: "2026-08-04T00:01:00Z",
        },
      ],
    });
  });
  await page.route(`**/api/agent-kernel/knowledge-bases/${kbId}/documents`, async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Agent Workbench" })).toBeVisible();
  await expect(page.getByLabel("Runtime status")).toContainText(/Checking API|API reachable|API unreachable/);
  await expect(page.getByRole("heading", { name: "Workspace sign in" })).toBeVisible();

  await page.getByRole("button", { name: "Continue anonymously" }).click();
  await expect(page.getByText("Anonymous (authentication disabled)")).toBeVisible();
  await expect(page.getByLabel("Workbench flow")).toContainText("Agents");
  await expect(page.getByLabel("Workbench flow")).toContainText("Results");
  await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Knowledge" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Agents" }).getByRole("combobox")).toContainText("Ops Agent");
  await expect(page.getByRole("region", { name: "Knowledge" }).getByRole("combobox").first())
    .toContainText("Live Operations KB");
  await expect(page.getByText("Advanced options")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Results" })).toHaveCount(0);
});

test("live Workbench surfaces run results after lookup", async ({ page }) => {
  await page.route("**/api/agent-kernel/health", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: { state: "online", baseUrl: "http://api:8000" },
    });
  });
  await page.route("**/api/agent-kernel/auth/me", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        authenticated: false,
        principal_id: null,
        display_name: null,
        workspace_id: null,
        role: null,
        permissions: [],
      },
    });
  });
  await page.route("**/api/agent-kernel/agents", async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  await page.route("**/api/agent-kernel/knowledge-bases", async (route) => {
    await route.fulfill({ contentType: "application/json", json: [] });
  });
  await page.route(`**/api/agent-kernel/runs/${runId}`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        id: runId,
        agent_id: agentId,
        status: "waiting_approval",
        input: { task: "lookup smoke" },
        output: null,
        error_type: null,
        error_message: null,
        created_at: "2026-08-04T00:00:00Z",
        updated_at: "2026-08-04T00:01:00Z",
      },
    });
  });
  await page.route(`**/api/agent-kernel/runs/${runId}/events`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          id: "evt-1",
          run_id: runId,
          sequence: 1,
          type: "run_waiting_approval",
          payload: { reason: "tool requires review" },
          created_at: "2026-08-04T00:01:00Z",
        },
      ],
    });
  });
  await page.route("**/api/agent-kernel/approvals", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          id: "live_appr_001",
          run_id: runId,
          tool_call_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          status: "requested",
          reason: "Live external write requires review",
          requested_by: null,
          reviewed_by: null,
          decision_note: null,
          trace_id: "live-trace",
          requested_at: "2026-08-04T00:00:00Z",
          resolved_at: null,
        },
      ],
    });
  });
  await page.route("**/api/agent-kernel/approvals/live_appr_001/tool-call", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        run_id: runId,
        approval_id: "live_appr_001",
        tool_name: "external_write",
        arguments: { path: "/tmp/demo" },
        risk_level: "high",
        status: "waiting_approval",
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Continue anonymously" }).click();
  await page.getByLabel("Run ID").fill(runId);
  await page.getByRole("button", { name: "Lookup run" }).click();
  await expect(page.getByRole("heading", { name: "Results" })).toBeVisible();
  await expect(page.getByTestId("run-status")).toHaveText("waiting_approval");
  await expect(page.getByRole("heading", { name: /Approvals/ })).toBeVisible();
  await expect(page.getByText("external_write")).toBeVisible();
  await expect(page.getByLabel("Run events")).toContainText("run_waiting_approval");
  await expect(page.getByTestId("run-output")).toContainText("No output yet.");
});
