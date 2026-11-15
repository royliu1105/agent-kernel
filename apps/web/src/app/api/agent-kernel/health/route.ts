import { apiOrigin, boundedBody, PRIVATE_HEADERS } from "../../../../lib/proxy";

export async function GET() {
  const checkedAt = new Date().toISOString();
  const started = Date.now();
  let baseUrl = "unconfigured";
  try {
    baseUrl = apiOrigin();
    const signal = AbortSignal.timeout(1500);
    const response = await fetch(`${baseUrl}/healthz`, {
      headers: { accept: "application/json" }, cache: "no-store",
      credentials: "omit", redirect: "error", signal,
    });
    if (!response.ok) {
      await response.body?.cancel();
      throw new Error("Health check failed");
    }
    const data = await boundedBody(response.body, 16 * 1024, signal);
    JSON.parse(new TextDecoder().decode(data));
    return Response.json({ state: "online", service: "agent-kernel-api", status: "ok",
      baseUrl, checkedAt, latencyMs: Date.now() - started }, { headers: PRIVATE_HEADERS });
  } catch {
    return Response.json({ state: "offline", service: "agent-kernel-api", status: "unreachable",
      baseUrl, checkedAt, latencyMs: null, error: "Health check failed." }, { headers: PRIVATE_HEADERS });
  }
}
