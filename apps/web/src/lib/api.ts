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

export type ApprovalStatus = "requested" | "approved" | "rejected" | "expired" | "canceled";

export type LiveApproval = {
  id: string;
  run_id: string;
  tool_call_id: string;
  status: ApprovalStatus;
  reason: string;
  requested_by: string | null;
  reviewed_by: string | null;
  decision_note: string | null;
  trace_id: string | null;
  requested_at: string;
  resolved_at: string | null;
};

export type KnowledgeBaseSummary = {
  id: string;
  name: string;
  documents: number;
  indexedChunks: number;
  status: "active" | "indexing" | "failed";
};

export type KnowledgeBaseStatus = "active" | "archived";

export type LiveKnowledgeBase = {
  id: string;
  name: string;
  description: string;
  status: KnowledgeBaseStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LiveRetrievalCitation = {
  knowledge_base_id: string;
  document_id: string;
  document_title: string;
  document_source_uri: string;
  chunk_id: string;
  chunk_index: number;
  start_char: number;
  end_char: number;
};

export type LiveRetrievalResult = {
  content: string;
  score: number;
  citation: LiveRetrievalCitation;
  metadata: Record<string, unknown>;
};

export type LiveRetrievalResponse = {
  knowledge_base_id: string;
  query: string;
  model: string;
  results: LiveRetrievalResult[];
};

export type EvalReportSummary = {
  name: string;
  passed: boolean;
  passedCount: number;
  failedCount: number;
  caseCount: number;
};

export type RuntimeHealthState = "checking" | "online" | "offline";

export type RuntimeHealth = {
  state: RuntimeHealthState;
  service: string;
  status: string;
  baseUrl: string;
  checkedAt: string | null;
  latencyMs: number | null;
  error?: string;
};

export type LiveRun = {
  id: string;
  agent_id: string;
  status: RunStatus;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  trace_id: string | null;
  error_type: string | null;
  error_message: string | null;
  input_tokens_total: number;
  output_tokens_total: number;
  estimated_cost_total: number;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

export type LiveRunEvent = {
  id: string;
  run_id: string;
  sequence: number;
  type: string;
  payload: Record<string, unknown>;
  trace_id: string | null;
  created_at: string;
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
