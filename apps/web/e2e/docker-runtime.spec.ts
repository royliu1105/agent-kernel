import { expect, test } from "@playwright/test";

test("Docker Web uses the internal API and renders on desktop and mobile", async ({ page, request }, testInfo) => {
  test.skip(process.env.AGENT_KERNEL_TEST_DOCKER_WEB !== "1", "Requires the Docker local stack");
  const response = await request.get("/api/agent-kernel/health");
  expect(response.ok()).toBeTruthy();
  const health = await response.json();
  expect(health.state).toBe("online");
  expect(health.baseUrl).toBe("http://api:8000");
  const knowledge = await request.get("/api/agent-kernel/knowledge-bases");
  expect(knowledge.ok()).toBeTruthy();
  expect(Array.isArray(await knowledge.json())).toBeTruthy();

  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Agent Workbench" })).toBeVisible();
    await expect(page.getByLabel("Runtime status")).toContainText("API reachable");
    await page.screenshot({ path: testInfo.outputPath(`docker-${viewport.width}.png`), fullPage: true });
  }
});
