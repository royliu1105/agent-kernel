export type RunStatus =
  | "created"
  | "queued"
  | "running"
  | "waiting_approval"
  | "resuming"
  | "succeeded"
  | "failed"
  | "canceled";

export type RunSummary = {
  id: string;
  agentId: string;
  status: RunStatus;
  traceId: string;
  task: string;
  model: string;
  latencyMs: number | null;
  estimatedCost: number;
  updatedAt: string;
};

export type RunEventSummary = {
  sequence: number;
  type: string;
  status: "complete" | "active" | "waiting" | "failed";
  label: string;
  detail: string;
};

export type ApprovalSummary = {
  id: string;
  runId: string;
  toolName: string;
  riskLevel: "read_only" | "external_write" | "filesystem_write" | "network" | "dangerous";
  reason: string;
  requestedAt: string;
};

export type KnowledgeBaseSummary = {
  id: string;
  name: string;
  documents: number;
  indexedChunks: number;
  status: "active" | "indexing" | "failed";
};

export type EvalReportSummary = {
  name: string;
  passed: boolean;
  passedCount: number;
  failedCount: number;
  caseCount: number;
};

export type WorkbenchSnapshot = {
  runs: RunSummary[];
  timeline: RunEventSummary[];
  approvals: ApprovalSummary[];
  knowledgeBases: KnowledgeBaseSummary[];
  evalReports: EvalReportSummary[];
};

export class ApiClient {
  private readonly baseUrl: string;

  constructor(baseUrl = process.env.NEXT_PUBLIC_AGENT_KERNEL_API_URL ?? "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getRun(runId: string): Promise<RunSummary> {
    return this.request<RunSummary>(`/v1/runs/${runId}`);
  }

  async getRunEvents(runId: string): Promise<RunEventSummary[]> {
    return this.request<RunEventSummary[]>(`/v1/runs/${runId}/events`);
  }

  private async request<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: { accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Agent Kernel API returned ${response.status}`);
    }
    return (await response.json()) as T;
  }
}
