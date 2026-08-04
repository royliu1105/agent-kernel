import { NextResponse } from "next/server";

const DEFAULT_API_URL = "http://127.0.0.1:8000";
const HEALTH_TIMEOUT_MS = 1500;

export async function GET() {
  const baseUrl = (process.env.NEXT_PUBLIC_AGENT_KERNEL_API_URL ?? DEFAULT_API_URL).replace(
    /\/$/,
    "",
  );
  const checkedAt = new Date().toISOString();
  const startedAt = Date.now();

  try {
    const response = await fetch(`${baseUrl}/healthz`, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    const latencyMs = Date.now() - startedAt;

    if (!response.ok) {
      return NextResponse.json({
        state: "offline",
        service: "agent-kernel-api",
        status: "unreachable",
        baseUrl,
        checkedAt,
        latencyMs,
        error: `Health check returned HTTP ${response.status}`,
      });
    }

    const payload = (await response.json()) as { service?: unknown; status?: unknown };

    return NextResponse.json({
      state: "online",
      service: typeof payload.service === "string" ? payload.service : "agent-kernel-api",
      status: typeof payload.status === "string" ? payload.status : "ok",
      baseUrl,
      checkedAt,
      latencyMs,
    });
  } catch (error) {
    return NextResponse.json({
      state: "offline",
      service: "agent-kernel-api",
      status: "unreachable",
      baseUrl,
      checkedAt,
      latencyMs: null,
      error: error instanceof Error ? error.message : "Health check failed",
    });
  }
}
