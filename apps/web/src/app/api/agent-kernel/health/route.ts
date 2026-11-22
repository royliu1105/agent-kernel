import { apiOrigin, boundedBody, PRIVATE_HEADERS } from "../../../../lib/proxy";

const DEFAULT_GRAFANA_URL = "http://127.0.0.1:3090";

function grafanaUrl(): string {
  const fromEnv = process.env.AGENT_KERNEL_GRAFANA_URL?.trim()
    || process.env.NEXT_PUBLIC_AGENT_KERNEL_GRAFANA_URL?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  const port = process.env.AGENT_KERNEL_GRAFANA_PORT?.trim();
  if (port) return `http://127.0.0.1:${port}`;
  return DEFAULT_GRAFANA_URL;
}

type DependencyStatus = { required?: boolean; status?: string };

async function readJson(url: string, signal: AbortSignal, limit: number): Promise<unknown> {
  const response = await fetch(url, {
    headers: { accept: "application/json" }, cache: "no-store",
    credentials: "omit", redirect: "error", signal,
  });
  if (!response.ok) {
    await response.body?.cancel();
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await boundedBody(response.body, limit, signal);
  return JSON.parse(new TextDecoder().decode(data));
}

function readinessSummary(body: unknown): {
  status: string;
  failing: string[];
} | null {
  if (!body || typeof body !== "object") return null;
  const record = body as { status?: unknown; dependencies?: unknown };
  const status = typeof record.status === "string" ? record.status : "unknown";
  const failing: string[] = [];
  if (record.dependencies && typeof record.dependencies === "object") {
    for (const [name, value] of Object.entries(record.dependencies as Record<string, DependencyStatus>)) {
      if (value?.required && value.status && value.status !== "ok" && value.status !== "disabled") {
        failing.push(name);
      }
    }
  }
  return { status, failing };
}

export async function GET() {
  const checkedAt = new Date().toISOString();
  const started = Date.now();
  const observability = { grafanaUrl: grafanaUrl() };
  let baseUrl = "unconfigured";
  try {
    baseUrl = apiOrigin();
    const signal = AbortSignal.timeout(1500);
    await readJson(`${baseUrl}/healthz`, signal, 16 * 1024);
    let readiness: { status: string; failing: string[] } | null = null;
    try {
      const readyBody = await readJson(`${baseUrl}/readyz`, AbortSignal.timeout(1500), 64 * 1024);
      readiness = readinessSummary(readyBody);
    } catch {
      readiness = { status: "unreachable", failing: ["readyz"] };
    }
    return Response.json({
      state: "online",
      service: "agent-kernel-api",
      status: "ok",
      baseUrl,
      checkedAt,
      latencyMs: Date.now() - started,
      readiness,
      observability,
    }, { headers: PRIVATE_HEADERS });
  } catch {
    return Response.json({
      state: "offline",
      service: "agent-kernel-api",
      status: "unreachable",
      baseUrl,
      checkedAt,
      latencyMs: null,
      error: "Health check failed.",
      readiness: null,
      observability,
    }, { headers: PRIVATE_HEADERS });
  }
}
