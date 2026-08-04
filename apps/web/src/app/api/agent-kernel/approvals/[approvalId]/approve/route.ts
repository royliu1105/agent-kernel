import { NextResponse } from "next/server";

const DEFAULT_API_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 3000;

type RouteContext = {
  params: Promise<{
    approvalId: string;
  }>;
};

export async function POST(request: Request, context: RouteContext) {
  const { approvalId } = await context.params;
  const baseUrl = apiBaseUrl();
  const body = await request.text();

  try {
    const response = await fetch(
      `${baseUrl}/v1/approvals/${encodeURIComponent(approvalId)}/approve`,
      {
        body: body.length === 0 ? "{}" : body,
        headers: {
          accept: "application/json",
          "content-type": "application/json",
        },
        method: "POST",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      },
    );
    const payload = (await response.json().catch(() => null)) as unknown;

    if (!response.ok) {
      return NextResponse.json(
        {
          error: `Approval approve returned HTTP ${response.status}`,
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
        error: error instanceof Error ? error.message : "Approval approve failed",
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
