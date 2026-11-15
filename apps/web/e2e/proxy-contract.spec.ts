import { expect, test } from "@playwright/test";
import { GET, POST, DELETE } from "../src/app/api/agent-kernel/[...path]/route";

const id = "12345678-1234-1234-1234-123456789abc";
const context = (path: string) => ({ params: Promise.resolve({ path: path.split("/") }) });
const token = "synthetic-unit-key";
const origin = "https://workbench.example";
const originalFetch = globalThis.fetch;
const originalApi = process.env.AGENT_KERNEL_API_URL;
const originalOrigin = process.env.AGENT_KERNEL_WEB_ORIGIN;

test.beforeEach(() => {
  process.env.AGENT_KERNEL_API_URL = "http://api:8000";
  delete process.env.AGENT_KERNEL_WEB_ORIGIN;
});
test.afterEach(() => {
  globalThis.fetch = originalFetch;
  if (originalApi === undefined) delete process.env.AGENT_KERNEL_API_URL;
  else process.env.AGENT_KERNEL_API_URL = originalApi;
  if (originalOrigin === undefined) delete process.env.AGENT_KERNEL_WEB_ORIGIN;
  else process.env.AGENT_KERNEL_WEB_ORIGIN = originalOrigin;
});

function request(path: string, method = "GET", body?: string, extra: Record<string, string> = {}) {
  return new Request(`${origin}/api/agent-kernel/${path}`, {
    method, body,
    headers: { host: "workbench.example", origin, authorization: `Bearer ${token}`,
      "content-type": "application/json", ...extra },
  });
}

test("forwards only the caller's bearer to the fixed API and never caches", async () => {
  let seen: RequestInit | undefined;
  let target = "";
  globalThis.fetch = async (url, init) => {
    target = String(url); seen = init;
    return Response.json({ id }, { status: 201 });
  };
  const response = await POST(request("agents", "POST", '{"name":"Scoped"}', {
    cookie: "admin=secret", "x-workspace-id": "other", "x-agent-kernel-api-key": "shared-admin",
  }), context("agents"));
  expect(target).toBe("http://api:8000/v1/agents");
  const sent = new Headers(seen?.headers);
  expect(sent.get("authorization")).toBe(`Bearer ${token}`);
  expect([...sent.keys()].sort()).toEqual(["accept", "authorization", "content-type"]);
  expect(seen?.cache).toBe("no-store");
  expect(seen?.redirect).toBe("error");
  expect(seen?.credentials).toBe("omit");
  expect(response.status).toBe(201);
  expect(response.headers.get("cache-control")).toBe("no-store");
  expect(response.headers.get("vary")).toBe("Authorization");
});

test("anonymous calls never borrow another request's key", async () => {
  const observed: (string | null)[] = [];
  globalThis.fetch = async (_url, init) => {
    observed.push(new Headers(init?.headers).get("authorization"));
    return Response.json({ authenticated: false });
  };
  await GET(request("auth/me"), context("auth/me"));
  await GET(new Request(`${origin}/api/agent-kernel/auth/me`), context("auth/me"));
  expect(observed).toEqual([`Bearer ${token}`, null]);
});

test("rejects unsupported paths, methods, queries, origins and oversized bodies before fetch", async () => {
  let fetched = false;
  globalThis.fetch = async () => { fetched = true; return Response.json({}); };
  expect((await GET(request("unknown"), context("unknown"))).status).toBe(404);
  expect((await GET(request("agents/.."), context("agents/.."))).status).toBe(404);
  expect((await DELETE(request("agents", "DELETE"), context("agents"))).status).toBe(405);
  expect((await GET(request("agents?workspace_id=other"), context("agents"))).status).toBe(400);
  expect((await POST(request("agents", "POST", "{}", { origin: "https://evil.example" }), context("agents"))).status).toBe(403);
  expect((await POST(request("agents", "POST", "{}", { "sec-fetch-site": "cross-site" }), context("agents"))).status).toBe(403);
  expect((await POST(request("agents", "POST", JSON.stringify({ name: "x".repeat(262_144) })), context("agents"))).status).toBe(413);
  expect((await POST(request("agents", "POST", '{"workspace_id":"other"}'), context("agents"))).status).toBe(400);
  expect((await POST(request("agents", "POST", "not-json"), context("agents"))).status).toBe(400);
  expect((await POST(request("agents", "POST", "{}", { "content-type": "text/plain" }), context("agents"))).status).toBe(415);
  expect(fetched).toBe(false);
});

test("passes multipart bytes without forwarding cookie credentials", async () => {
  const form = new FormData();
  form.set("file", new Blob(["# Synthetic operations"], { type: "text/markdown" }), "ops.md");
  let byteCount = 0;
  globalThis.fetch = async (_url, init) => {
    expect(new Headers(init?.headers).get("content-type")).toContain("multipart/form-data;");
    byteCount = (init?.body as ArrayBuffer).byteLength;
    return Response.json({ id }, { status: 201 });
  };
  const pathname = `knowledge-bases/${id}/documents/upload`;
  const result = await POST(new Request(`${origin}/api/agent-kernel/${pathname}`, {
    method: "POST", body: form, headers: { origin, host: "workbench.example", authorization: `Bearer ${token}` },
  }), context(pathname));
  expect(result.status).toBe(201);
  expect(byteCount).toBeGreaterThan(20);
});

test("does not echo upstream details or transport exceptions", async () => {
  for (const status of [401, 403, 404, 409, 422, 500]) {
    globalThis.fetch = async () => Response.json({ detail: token }, { status });
    const response = await GET(request("auth/me"), context("auth/me"));
    expect(response.status).toBe(status === 500 ? 502 : status);
    expect(await response.text()).not.toContain(token);
    expect(response.headers.get("cache-control")).toBe("no-store");
  }
  globalThis.fetch = async () => { throw new Error(`private URL ${token}`); };
  const failed = await GET(request("auth/me"), context("auth/me"));
  expect(failed.status).toBe(502);
  expect(await failed.text()).not.toContain(token);
});

test("rejects invalid upstream configuration and oversized output", async () => {
  let called = false;
  globalThis.fetch = async () => { called = true; return Response.json({}); };
  process.env.AGENT_KERNEL_API_URL = "https://user:password@api.example";
  expect((await GET(request("auth/me"), context("auth/me"))).status).toBe(502);
  expect(called).toBe(false);
  process.env.AGENT_KERNEL_API_URL = "http://api:8000";
  globalThis.fetch = async () => Response.json({ data: "x".repeat(4 * 1024 * 1024) });
  expect((await GET(request("auth/me"), context("auth/me"))).status).toBe(502);
});

test("canonical origin supports TLS termination without trusting forwarded headers", async () => {
  globalThis.fetch = async () => Response.json({ id }, { status: 201 });
  process.env.AGENT_KERNEL_WEB_ORIGIN = origin;
  const response = await POST(new Request("http://web:3000/api/agent-kernel/agents", {
    method: "POST", body: "{}", headers: { host: "web:3000", origin,
      "content-type": "application/json", "x-forwarded-host": "untrusted.example" },
  }), context("agents"));
  expect(response.status).toBe(201);
  process.env.AGENT_KERNEL_WEB_ORIGIN = "https://user:secret@workbench.example";
  expect((await POST(request("agents", "POST", "{}"), context("agents"))).status).toBe(502);
});
