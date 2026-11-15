"use client";

import { useCallback, useEffect, useRef } from "react";

export type Identity = {
  authenticated: boolean;
  principal_id: string | null;
  display_name: string | null;
  workspace_id: string | null;
  role: string | null;
  permissions: string[];
};

export type Agent = { id: string; name: string; status: string };
export type Document = { id: string; title: string; status: string; knowledge_base_id: string };

export function isIdentity(value: unknown): value is Identity {
  if (!value || typeof value !== "object") return false;
  const data = value as Record<string, unknown>;
  return typeof data.authenticated === "boolean" &&
    ["principal_id", "display_name", "workspace_id", "role"].every(
      (key) => data[key] === null || typeof data[key] === "string",
    ) && Array.isArray(data.permissions) && data.permissions.every((p) => typeof p === "string");
}

export class RequestError extends Error {
  constructor(public status: number) {
    super(status === 401 ? "Session expired. Sign in again." :
      status === 403 ? "Permission denied." :
      status === 404 ? "Resource not found." :
      status === 409 ? "Action conflicts with the current state. Refresh before continuing." :
      status === 413 ? "Request is too large." :
      status === 422 || status === 400 ? "Check the request fields." :
      status === 429 ? "Too many requests. Try again later." :
      "Request failed. Refresh to check the result before repeating an action.");
  }
}

export function useLiveApi(token: string, onUnauthorized: () => void) {
  const pending = useRef(new Set<AbortController>());
  useEffect(() => {
    const controllers = pending.current;
    return () => {
      for (const controller of controllers) controller.abort();
      controllers.clear();
    };
  }, []);

  return useCallback(async <T,>(path: string, body?: Record<string, unknown> | FormData): Promise<T> => {
    const controller = new AbortController();
    pending.current.add(controller);
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(125_000)]);
    try {
      const headers = new Headers({ accept: "application/json" });
      if (token) headers.set("authorization", `Bearer ${token}`);
      const multipart = body instanceof FormData;
      if (body && !multipart) headers.set("content-type", "application/json");
      const response = await fetch(`/api/agent-kernel/${path}`, {
        method: body === undefined ? "GET" : "POST",
        headers,
        body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
        credentials: "omit", cache: "no-store", redirect: "error", signal,
      });
      signal.throwIfAborted();
      if (response.status === 401) onUnauthorized();
      if (!response.ok) throw new RequestError(response.status);
      const result: T = await response.json();
      signal.throwIfAborted();
      return result;
    } finally {
      pending.current.delete(controller);
    }
  }, [token, onUnauthorized]);
}

export function errorMessage(error: unknown) {
  return error instanceof RequestError ? error.message :
    "Request failed. Refresh to check the result before repeating an action.";
}
