import { apiOrigin, boundedBody, BodyLimitError, PRIVATE_HEADERS, proxyError } from "../../../../lib/proxy";

const UUID = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const routes: [RegExp, string[]][] = [
  [/^auth\/me$/, ["GET"]],
  [/^agents$/, ["GET", "POST"]],
  [new RegExp(`^agents/${UUID}$`), ["GET"]],
  [new RegExp(`^agents/${UUID}/runs$`), ["POST"]],
  [new RegExp(`^runs/${UUID}(?:/events)?$`), ["GET"]],
  [new RegExp(`^runs/${UUID}/(?:queue|cancel|resume)$`), ["POST"]],
  [/^knowledge-bases$/, ["GET", "POST"]],
  [new RegExp(`^knowledge-bases/${UUID}(?:/documents)?$`), ["GET"]],
  [new RegExp(`^knowledge-bases/${UUID}/(?:documents/upload|retrieve)$`), ["POST"]],
  [new RegExp(`^documents/${UUID}(?:/chunks|/ingestion-jobs)?$`), ["GET"]],
  [new RegExp(`^documents/${UUID}/(?:ingest|chunk|index)$`), ["POST"]],
  [/^approvals$/, ["GET"]],
  [new RegExp(`^approvals/${UUID}(?:/tool-call)?$`), ["GET"]],
  [new RegExp(`^approvals/${UUID}/(?:approve|reject)$`), ["POST"]],
  [/^evals\/runs$/, ["GET"]],
];
const JSON_LIMIT = 256 * 1024;
const UPLOAD_LIMIT = 9 * 1024 * 1024;
const OUTPUT_LIMIT = 4 * 1024 * 1024;

async function proxy(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path: segments } = await context.params;
  const path = segments.join("/");
  if (segments.some((segment) => !/^[a-zA-Z0-9-]+$/.test(segment))) return proxyError(404);
  const rule = routes.find(([pattern]) => pattern.test(path));
  if (!rule) return proxyError(404);
  if (!rule[1].includes(request.method)) return proxyError(405);
  const url = new URL(request.url);
  const query = new URLSearchParams();
  for (const [key, value] of url.searchParams) {
    if (path !== "approvals" || key !== "status" || query.has(key) ||
        !["requested", "approved", "rejected", "expired", "canceled"].includes(value)) {
      return proxyError(400);
    }
    query.set(key, value);
  }
  if (request.method === "POST") {
    const origin = request.headers.get("origin");
    const site = request.headers.get("sec-fetch-site");
    // Use the actual Host and protocol, never client-supplied forwarded headers.
    let expected = `${url.protocol}//${request.headers.get("host") ?? url.host}`;
    const configured = process.env.AGENT_KERNEL_WEB_ORIGIN;
    if (configured) {
      try {
        const canonical = new URL(configured);
        if (!["https:", "http:"].includes(canonical.protocol) || canonical.username || canonical.password ||
            canonical.pathname !== "/" || canonical.search || canonical.hash) return proxyError(502);
        expected = canonical.origin;
      } catch { return proxyError(502); }
    }
    if (!origin || origin !== expected || (site && site !== "same-origin")) return proxyError(403);
  }
  const headers = new Headers({ accept: "application/json" });
  const authorization = request.headers.get("authorization");
  if (authorization !== null) {
    if (!/^Bearer [A-Za-z0-9._~+\/-]+=*$/i.test(authorization) || authorization.length > 4096) {
      return proxyError(401);
    }
    headers.set("authorization", authorization);
  }
  const signal = AbortSignal.any([request.signal, AbortSignal.timeout(120_000)]);
  let body: ArrayBuffer | undefined;
  try {
    if (request.method === "POST") {
      const upload = path.endsWith("/documents/upload");
      const type = request.headers.get("content-type") ?? "";
      const limit = upload ? UPLOAD_LIMIT : JSON_LIMIT;
      if (Number(request.headers.get("content-length")) > limit) return proxyError(413);
      body = await boundedBody(request.body, limit, signal);
      if (upload) {
        if (!/^multipart\/form-data;\s*boundary=[\x20-\x7e]{1,200}$/i.test(type)) return proxyError(415);
      } else if (body.byteLength) {
        if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(type)) return proxyError(415);
        try {
          const json: unknown = JSON.parse(new TextDecoder().decode(body));
          if (!json || typeof json !== "object" || Array.isArray(json) ||
              Object.keys(json).some((key) => ["workspace_id", "principal_id", "workspace"].includes(key))) {
            return proxyError(400);
          }
        } catch { return proxyError(400); }
      }
      if (type) headers.set("content-type", type);
    }
  } catch (error) {
    return proxyError(error instanceof BodyLimitError ? 413 : 400);
  }
  try {
    const suffix = query.size ? `?${query}` : "";
    const response = await fetch(`${apiOrigin()}/v1/${path}${suffix}`, {
      method: request.method, headers, body, cache: "no-store", credentials: "omit",
      redirect: "error", signal,
    });
    if (!response.ok) {
      await response.body?.cancel();
      return proxyError(response.status >= 400 && response.status < 500 ? response.status : 502);
    }
    if (!response.headers.get("content-type")?.includes("application/json")) {
      await response.body?.cancel();
      return proxyError(502);
    }
    const data = await boundedBody(response.body, OUTPUT_LIMIT, signal);
    const payload: unknown = JSON.parse(new TextDecoder().decode(data));
    return Response.json(payload, { status: response.status, headers: PRIVATE_HEADERS });
  } catch {
    return proxyError(502);
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE,
  proxy as HEAD, proxy as OPTIONS };
