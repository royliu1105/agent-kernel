import { NextResponse } from "next/server";

const DEFAULT_API_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 3000;

export async function GET() {
  const baseUrl = apiBaseUrl();

  try {
    const response = await fetch(`${baseUrl}/v1/evals/runs`, {
      headers: { accept: "application/json" },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    const payload = (await response.json().catch(() => null)) as unknown;

    if (!response.ok) {
      return NextResponse.json(
        {
          error: `Eval run list returned HTTP ${response.status}`,
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
        error: error instanceof Error ? error.message : "Eval run list lookup failed",
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
