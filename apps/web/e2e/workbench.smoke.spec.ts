import { expect, test } from "@playwright/test";

test("operator can navigate core Workbench views", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Agent Workbench" })).toBeVisible();
  await expect(page.getByLabel("Runtime status")).toContainText("Local UI state");

  await page.getByRole("button", { name: "Agents" }).click();
  await expect(page.getByRole("heading", { name: "Agents" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Research Agent" })).toBeVisible();
  await expect(page.getByText("memory_search")).toBeVisible();

  await page.getByRole("button", { name: "Knowledge" }).click();
  await expect(page.getByRole("heading", { name: "Knowledge" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Document ingestion" })).toBeVisible();
  await expect(page.getByText("rollback-playbook.md")).toBeVisible();

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
  await page.goto("/");

  await page.getByRole("button", { name: "Runs" }).click();
  await expect(page.getByRole("heading", { name: "Runs" })).toBeVisible();
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
  await expect(page.getByText("Decisions here are local UI state for Day 32.")).toBeVisible();

  await page.getByRole("button", { name: "Approve" }).first().click();
  await expect(page.getByText("approved · just now")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Decision history" })).toBeVisible();
  await expect(page.getByText("appr_421")).toBeVisible();
});
