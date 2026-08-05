import { expect, test } from "@playwright/test";

test("operator can navigate core Workbench views", async ({ page }) => {
  await page.route("**/api/agent-kernel/knowledge-bases", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          id: "33333333-3333-4333-8333-333333333333",
          name: "Live Operations KB",
          description: "Knowledge base returned by live API",
          status: "active",
          metadata: {},
          created_at: "2026-08-04T00:00:00Z",
          updated_at: "2026-08-04T00:01:00Z",
        },
      ],
    });
  });
  await page.route(
    "**/api/agent-kernel/knowledge-bases/33333333-3333-4333-8333-333333333333/retrieve",
    async (route) => {
      await route.fulfill({
        contentType: "application/json",
        json: {
          knowledge_base_id: "33333333-3333-4333-8333-333333333333",
          query: "rollback",
          model: "mock-embedding",
          results: [
            {
              content: "Use the rollback playbook when deployment health checks fail.",
              score: 0.9123,
              citation: {
                knowledge_base_id: "33333333-3333-4333-8333-333333333333",
                document_id: "44444444-4444-4444-8444-444444444444",
                document_title: "Rollback Playbook",
                document_source_uri: "memory://rollback-playbook.md",
                chunk_id: "55555555-5555-4555-8555-555555555555",
                chunk_index: 0,
                start_char: 0,
                end_char: 62,
              },
              metadata: {},
            },
          ],
        },
      });
    },
  );

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Agent Workbench" })).toBeVisible();
  await expect(page.getByLabel("Runtime status")).toContainText(
    /Checking API|API reachable|API unreachable/,
  );
  await expect(page.getByLabel("Workbench data scope")).toContainText("Public Alpha");
  await expect(page.getByText("Live where it matters for first-run verification.")).toBeVisible();

  await page.getByRole("button", { name: "Agents" }).click();
  await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Research Agent" })).toBeVisible();
  await expect(page.getByText("memory_search")).toBeVisible();

  await page.getByRole("button", { name: "Knowledge" }).click();
  await expect(page.getByRole("heading", { name: "Knowledge", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Knowledge base list" })).toBeVisible();
  await expect(page.getByText("Live Operations KB")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Retrieval search" })).toBeVisible();
  await page.getByRole("button", { name: "Use for search" }).click();
  await page.getByLabel("Search query").fill("rollback");
  await page.getByRole("button", { name: "Search live" }).click();
  await expect(page.getByText("Rollback Playbook", { exact: true })).toBeVisible();
  await expect(page.getByText("memory://rollback-playbook.md")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Document ingestion" })).toBeVisible();
  await expect(page.getByText("rollback-playbook.md", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Release Notes" }).click();
  await expect(page.getByText("2026-07-release-notes.md")).toBeVisible();
  await expect(page.getByText("migration-checklist.md")).toBeVisible();

  await page.getByRole("button", { name: "Evals" }).click();
  await expect(page.getByRole("heading", { name: "Evals" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Behavior cases" })).toBeVisible();
  await expect(page.getByText("Return cited rollback guidance")).toBeVisible();

  await page.getByRole("button", { name: "tool-regression" }).click();
  await expect(page.getByText("Replay lookup uses registered model")).toBeVisible();
  await expect(page.getByText("Replay fixture missing")).toBeVisible();

  await page.getByRole("button", { name: "Settings" }).click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByText("API endpoint")).toBeVisible();
  await expect(page.getByText("approval required")).toBeVisible();
});

test("operator can inspect runs and approve tool calls locally", async ({ page }) => {
  await page.route("**/api/agent-kernel/approvals", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: [
        {
          id: "live_appr_001",
          run_id: "11111111-1111-4111-8111-111111111111",
          tool_call_id: "22222222-2222-4222-8222-222222222222",
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
  await page.route("**/api/agent-kernel/approvals/live_appr_001/approve", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      json: {
        id: "live_appr_001",
        run_id: "11111111-1111-4111-8111-111111111111",
        tool_call_id: "22222222-2222-4222-8222-222222222222",
        status: "approved",
        reason: "Live external write requires review",
        requested_by: null,
        reviewed_by: null,
        decision_note: "Approved from Workbench",
        trace_id: "live-trace",
        requested_at: "2026-08-04T00:00:00Z",
        resolved_at: "2026-08-04T00:01:00Z",
      },
    });
  });

  await page.goto("/");

  await page.getByRole("button", { name: "Runs" }).click();
  await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Run lookup" })).toBeVisible();

  await page.getByRole("button", { name: "Lookup" }).click();
  await expect(page.getByText("Enter a run ID first.")).toBeVisible();

  await expect(page.getByRole("heading", { name: "run_9b1c" })).toBeVisible();
  await expect(page.getByText("Approval waiting")).toBeVisible();
  await expect(page.getByText("Tool call ID")).toBeVisible();
  await expect(page.getByText("tool_902")).toBeVisible();

  await page.getByRole("button", { name: /Search release notes knowledge base/ }).click();
  await expect(page.getByRole("heading", { name: "run_7e42" })).toBeVisible();
  await expect(page.getByText("kb_search completed")).toBeVisible();
  await expect(page.getByText("tool_812")).toBeVisible();

  await page.getByRole("button", { name: "Approvals" }).click();
  await expect(page.getByRole("heading", { name: "Approval inbox" })).toBeVisible();
  await expect(page.getByLabel("Live approvals status")).toContainText(
    /Loading live approvals|live approvals from API|Live approvals unavailable|Approval list/,
  );
  await expect(page.getByText("Live external write requires review")).toBeVisible();
  await page.getByRole("button", { name: "Approve live" }).click();
  await expect(page.getByText("approved · 2026-08-04T00:01:00Z")).toBeVisible();
  await expect(page.getByText(/approval cards below are preview data/)).toBeVisible();

  await page.getByRole("button", { name: /^Approve$/ }).first().click();
  await expect(page.getByText("approved · just now")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Decision history" })).toBeVisible();
  await expect(page.getByText("appr_421")).toBeVisible();
});
