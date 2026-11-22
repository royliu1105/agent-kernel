/** Operator Grafana links for the local/default observability stack. */

export const DEFAULT_GRAFANA_URL = "http://127.0.0.1:3090";

const LOKI_UID = "agent-kernel-loki";
const TEMPO_UID = "agent-kernel-tempo";
const DASHBOARD_UID = "agent-kernel-operations";

function grafanaBase(baseUrl?: string | null): string {
  const raw = (baseUrl ?? process.env.NEXT_PUBLIC_AGENT_KERNEL_GRAFANA_URL ?? DEFAULT_GRAFANA_URL).trim();
  return raw.replace(/\/$/, "") || DEFAULT_GRAFANA_URL;
}

function exploreUrl(baseUrl: string | null | undefined, pane: Record<string, unknown>): string {
  const panes = { ak: pane };
  const params = new URLSearchParams({
    schemaVersion: "1",
    orgId: "1",
    panes: JSON.stringify(panes),
  });
  return `${grafanaBase(baseUrl)}/explore?${params.toString()}`;
}

export function grafanaLogsUrl(runId: string, baseUrl?: string | null): string {
  return exploreUrl(baseUrl, {
    datasource: LOKI_UID,
    queries: [{
      refId: "A",
      expr: `{job="agent-kernel"} | json | run_id="${runId}"`,
      queryType: "range",
    }],
    range: { from: "now-6h", to: "now" },
  });
}

export function grafanaTraceUrl(traceId: string, baseUrl?: string | null): string {
  return exploreUrl(baseUrl, {
    datasource: TEMPO_UID,
    queries: [{
      refId: "A",
      query: traceId,
      queryType: "traceql",
    }],
    range: { from: "now-6h", to: "now" },
  });
}

export function grafanaDashboardUrl(baseUrl?: string | null): string {
  return `${grafanaBase(baseUrl)}/d/${DASHBOARD_UID}/agent-kernel-operations?orgId=1`;
}

export function formatRunCost(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (value === 0) return "0";
  if (Math.abs(value) >= 0.01) return value.toFixed(4);
  return value.toFixed(6);
}
