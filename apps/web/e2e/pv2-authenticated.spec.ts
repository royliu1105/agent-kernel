import { expect, test, type Page, type APIRequestContext } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";

test.skip(!process.env.CF2_WEB_PROJECT, "Requires the owned remote-CI Docker fixture");

type Credentials = Record<string, { key: string; workspace_id: string }>;
type Observation = {
  status: string;
  calls: { status: string; approval_id: string | null }[];
  effects: number;
  prompt_hashes: string[];
  provider_calls: number;
  output: { text: string } | null;
};
const base = "/api/agent-kernel";

function credentials(): Credentials {
  return JSON.parse(readFileSync(path.join(process.env.CF2_WEB_EVIDENCE!, "credentials.json"), "utf8"));
}

function observer(command: string, runId?: string): Observation {
  const project = process.env.CF2_WEB_PROJECT!;
  if (process.env.GITHUB_ACTIONS !== "true" || !/^agent-kernel-cf2-[a-f0-9]{16}$/.test(project)) {
    throw new Error("Refusing an unowned observer target");
  }
  return JSON.parse(execFileSync("docker", [
    "compose", "--env-file", "/dev/null", "-f",
    path.join(process.env.CF2_WEB_EVIDENCE!, "compose.json"), "-p", project,
    "exec", "-T", "api", "python", "/fixture/pv2_web_observer.py", command,
    ...(runId ? [runId] : []),
  ], { encoding: "utf8", timeout: 60_000 }));
}

function headers(key: string) { return { Authorization: `Bearer ${key}` }; }

async function signIn(page: Page, key: string) {
  await page.goto("/");
  await page.getByLabel("API key", { exact: true }).fill(key);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeVisible();
}

async function clickPost(page: Page, button: string, suffix: string) {
  const response = page.waitForResponse(r => r.request().method() === "POST" && r.url().endsWith(suffix));
  await page.getByRole("button", { name: button, exact: true }).click();
  const result = await response;
  expect(result.ok(), `${button} HTTP status`).toBeTruthy();
  return result.json();
}

async function status(request: APIRequestContext, key: string, runId: string) {
  const response = await request.get(`${base}/runs/${runId}`, { headers: headers(key) });
  expect(response.status()).toBe(200);
  return (await response.json()).status;
}

test("real authenticated Web first use and independent execution evidence", async ({ page, browser, request }) => {
  const keys = credentials();
  const origin = process.env.PLAYWRIGHT_BASE_URL!;
  const operator = headers(keys.operator.key);
  expect((await request.get(`${base}/auth/me`)).status()).toBe(401);
  expect((await request.get(`${base}/auth/me`, { headers: headers("invalid-fixture-key") })).status()).toBe(401);
  const identity = await request.get(`${base}/auth/me`, { headers: operator });
  expect(identity.headers()["cache-control"]).toContain("no-store");
  expect((await identity.json()).role).toBe("operator");
  expect((await request.post(`${base}/agents`, { headers: { ...operator, Origin: "https://untrusted.invalid" }, data: { name: "forbidden" } })).status()).toBe(403);
  expect((await request.get(`${base}/unknown`, { headers: operator })).status()).toBe(404);
  expect((await request.get(`${base}/agents?upstream=https://untrusted.invalid`, { headers: operator })).status()).toBe(400);

  await signIn(page, keys.operator.key);
  await page.getByLabel("Agent name", { exact: true }).fill("Web first use");
  const agent = await clickPost(page, "Create agent", "/agents");
  await page.getByLabel("Knowledge base name", { exact: true }).fill("Web synthetic operations");
  const kb = await clickPost(page, "Create knowledge base", "/knowledge-bases");
  await expect(page.getByLabel("Document file", { exact: true })).toBeEnabled();
  await page.getByLabel("Document file", { exact: true }).setInputFiles({
    name: "operations.md", mimeType: "text/markdown",
    buffer: Buffer.from("# CF2 synthetic operations\n\nThe CF2 hatch is blue.\n"),
  });
  const document = await clickPost(page, "Upload document", `/knowledge-bases/${kb.id}/documents/upload`);
  await clickPost(page, "Ingest document", `/documents/${document.id}/ingest`);
  await clickPost(page, "Chunk document", `/documents/${document.id}/chunk`);
  const index = await clickPost(page, "Index document", `/documents/${document.id}/index`);
  expect(index.embedding_count).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Inspect chunks", exact: true }).click();
  await page.getByText("Document result", { exact: true }).click();
  await expect(page.getByRole("group").filter({ hasText: "Document result" })).toContainText("The CF2 hatch is blue");
  await page.getByLabel("Search query", { exact: true }).fill("CF2 hatch blue");
  await clickPost(page, "Retrieve", `/knowledge-bases/${kb.id}/retrieve`);
  await expect(page.getByTestId("retrieval-results")).toContainText(document.id);

  const createWaiting = async (name: string) => {
    const advanced = page.getByTestId("run-advanced-options");
    await advanced.scrollIntoViewIfNeeded();
    // Keep the panel open across repeated createWaiting calls; a second summary
    // click would close it and make System prompt unfillable.
    if (!(await advanced.evaluate((el) => (el as HTMLDetailsElement).open))) {
      await advanced.locator("summary").click();
    }
    await expect(advanced).toHaveAttribute("open", "");
    await advanced.getByLabel("System prompt", { exact: true }).fill(readFileSync(
      path.resolve("../../docs/pilots/prompts/pv1-runbook-assistant-v1.txt"), "utf8",
    ));
    await page.getByLabel("Model", { exact: true }).fill("openai:cf2-offline");
    await page.getByLabel("Task", { exact: true }).fill(JSON.stringify({ case: name, kb_id: kb.id }));
    const run = await clickPost(page, "Create run", `/agents/${agent.id}/runs`);
    await clickPost(page, "Queue run", `/runs/${run.id}/queue`);
    await expect.poll(() => status(request, keys.operator.key, run.id), { timeout: 60_000 }).toBe("waiting_approval");
    await page.getByRole("button", { name: "Refresh run", exact: true }).click();
    await expect(page.getByTestId("run-status")).toHaveText("waiting_approval");
    const approvals = await request.get(`${base}/approvals`, { headers: operator });
    const approval = (await approvals.json()).find((item: { run_id: string }) => item.run_id === run.id);
    expect(approval.status).toBe("requested");
    expect(observer("observe", run.id).effects).toBe(0);
    return { run, approval };
  };

  const { run, approval } = await createWaiting("web-approved");
  const viewerContext = await browser.newContext();
  const viewer = await viewerContext.newPage();
  await signIn(viewer, keys.viewer.key);
  await expect(viewer.getByRole("button", { name: "Create agent", exact: true })).toBeDisabled();
  expect((await request.post(`${base}/approvals/${approval.id}/approve`, {
    headers: { ...headers(keys.viewer.key), Origin: origin }, data: {},
  })).status()).toBe(403);
  expect((await request.get(`${base}/runs/${run.id}`, { headers: headers(keys.other.key) })).status()).toBe(404);
  const otherAgents = await request.get(`${base}/agents`, { headers: headers(keys.other.key) });
  expect(await otherAgents.json()).toEqual([]);
  expect(observer("observe", run.id).effects).toBe(0);
  await viewerContext.close();

  const card = page.getByTestId(`approval-${approval.id}`);
  await expect(card).toBeVisible();
  await expect(card).toContainText("inventory_lookup");
  await expect(card).toContainText("web-approved");
  const approved = page.waitForResponse(r => r.url().endsWith(`/approvals/${approval.id}/approve`));
  await card.getByRole("button", { name: "Approve", exact: true }).click();
  expect((await approved).ok()).toBeTruthy();
  const before = observer("observe", run.id);
  expect(before.effects).toBe(0);
  expect(before.status).toBe("waiting_approval");
  await clickPost(page, "Resume run", `/runs/${run.id}/resume`);
  await expect(page.getByTestId("run-status")).toHaveText("succeeded");
  await expect(page.getByTestId("run-output")).toContainText("The CF2 hatch is blue");
  await expect(page.getByTestId("run-output")).toContainText(document.id);
  const completed = observer("observe", run.id);
  expect(completed.effects).toBe(1);
  expect(completed.provider_calls).toBe(3);
  expect(completed.prompt_hashes).toEqual(["bf6c5329a3e3bfa8587947b53a904fe4c3193444ad1f24a947305f163b1b091b"]);
  expect(completed.calls.map(item => item.status)).toEqual(["succeeded", "succeeded"]);
  expect(JSON.parse(completed.output!.text).citation.document_id).toBe(document.id);
  expect((await request.post(`${base}/runs/${run.id}/resume`, {
    headers: { ...operator, Origin: origin }, data: { approval_id: approval.id },
  })).status()).toBe(409);
  expect(observer("observe", run.id).effects).toBe(1);

  const screenshots = path.resolve("../../.agent-kernel/pv2-web-screenshots");
  mkdirSync(screenshots, { recursive: true });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await page.screenshot({ path: path.join(screenshots, `workbench-${width}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  const rejected = await createWaiting("web-rejected");
  const rejectedCard = page.getByTestId(`approval-${rejected.approval.id}`);
  await rejectedCard.getByLabel("Decision note", { exact: true }).fill("Rejected synthetic operation");
  const rejection = page.waitForResponse(r => r.url().endsWith(`/approvals/${rejected.approval.id}/reject`));
  await rejectedCard.getByRole("button", { name: "Reject", exact: true }).click();
  expect((await rejection).ok()).toBeTruthy();
  expect(observer("observe", rejected.run.id).effects).toBe(0);
  await clickPost(page, "Resume run", `/runs/${rejected.run.id}/resume`);
  await expect(page.getByTestId("run-status")).toHaveText("failed");
  const denied = observer("observe", rejected.run.id);
  expect(denied.effects).toBe(0);
  expect(denied.calls.map(item => item.status)).toEqual(["succeeded", "denied"]);
  expect((await request.post(`${base}/runs/${rejected.run.id}/resume`, {
    headers: { ...operator, Origin: origin }, data: { approval_id: rejected.approval.id },
  })).status()).toBe(409);
  expect(observer("observe", rejected.run.id).effects).toBe(0);

  const storage = await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length, cookie: document.cookie }));
  expect(storage).toEqual({ local: 0, session: 0, cookie: "" });
  expect((await page.context().cookies()).length).toBe(0);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("API key", { exact: true })).toBeVisible();
  await expect(page.getByText("Web first use", { exact: true })).toHaveCount(0);
  await signIn(page, keys.operator.key);
  await page.reload();
  await expect(page.getByLabel("API key", { exact: true })).toBeVisible();
  await signIn(page, keys.operator.key);
  observer("revoke");
  await page.getByLabel("Agent name", { exact: true }).fill("Revoked must not create");
  await page.getByRole("button", { name: "Create agent", exact: true }).click();
  await expect(page.getByLabel("API key", { exact: true })).toBeVisible();
  await expect(page.getByText("Web first use", { exact: true })).toHaveCount(0);
  await page.reload();
  await page.getByLabel("API key", { exact: true }).fill(keys.operator.key);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out", exact: true })).toHaveCount(0);
  expect((await request.get(`${base}/auth/me`, { headers: operator })).status()).toBe(401);
  expect((await request.get(`${base}/auth/me`, { headers: headers(keys.viewer.key) })).status()).toBe(200);
  expect(observer("observe", run.id).effects).toBe(1);
});
