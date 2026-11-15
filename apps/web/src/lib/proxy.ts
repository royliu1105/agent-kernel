export const PRIVATE_HEADERS = {
  "Cache-Control": "no-store",
  Vary: "Authorization",
  "X-Content-Type-Options": "nosniff",
};

export class BodyLimitError extends Error {}

export function apiOrigin(): string {
  const value = process.env.AGENT_KERNEL_API_URL;
  if (!value) throw new Error("API is not configured");
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password ||
      url.search || url.hash || url.pathname !== "/") {
    throw new Error("Invalid API configuration");
  }
  return url.origin;
}

// Limit actual streamed bytes, not just the caller's Content-Length claim.
export async function boundedBody(
  body: ReadableStream<Uint8Array> | null,
  limit: number,
  signal: AbortSignal,
): Promise<ArrayBuffer> {
  if (!body) return new ArrayBuffer(0);
  const reader = body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  const cancel = () => { void reader.cancel().catch(() => undefined); };
  signal.addEventListener("abort", cancel, { once: true });
  try {
    signal.throwIfAborted();
    while (true) {
      const { value, done } = await reader.read();
      signal.throwIfAborted();
      if (done) break;
      size += value.byteLength;
      if (size > limit) {
        cancel();
        throw new BodyLimitError();
      }
      chunks.push(value);
    }
    const result = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      result.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return result.buffer;
  } finally {
    signal.removeEventListener("abort", cancel);
    reader.releaseLock();
  }
}

export function proxyError(status: number) {
  const error = status === 401 ? "Authentication required." :
    status === 403 ? "Request not permitted." :
    status === 413 ? "Request exceeds the size limit." :
    status === 404 ? "Resource not found." :
    status === 409 ? "Resource state conflicts with this action." :
    status === 422 || status === 400 || status === 415 ? "Invalid request." :
    status === 405 ? "Method not permitted." :
    status === 429 ? "Too many requests." : "API request failed.";
  return Response.json({ error }, { status, headers: PRIVATE_HEADERS });
}
