import { NextResponse } from "next/server";

const DEFAULT_API_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 3000;

type RouteContext = {
  params: Promise<{
    runId: string;
  }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const { runId } = await context.params;
  const baseUrl = apiBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/v1/runs/${encodeURIComponent(runId)}`, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    const payload = (await response.json().catch(() => null)) as unknown;

    if (!response.ok) {
      return NextResponse.json(
        {
          error: `Run lookup returned HTTP ${response.status}`,
          status: response.status,
          detail: payload,
        },
        { status: response.status },
      );
    }

    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Run lookup failed",
        status: 503,
      },
      { status: 503 },
    );
  }
}

function apiBaseUrl() {
  return (
    process.env.AGENT_KERNEL_API_URL ??
    process.env.NEXT_PUBLIC_AGENT_KERNEL_API_URL ??
    DEFAULT_API_URL
  ).replace(/\/$/, "");
}
