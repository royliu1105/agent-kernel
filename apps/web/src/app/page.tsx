"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import type {
  ApprovalSummary,
  EvalReportSummary,
  KnowledgeBaseSummary,
  LiveApproval,
  LiveKnowledgeBase,
  LiveRetrievalResponse,
  LiveRun,
  LiveRunEvent,
  RuntimeHealth,
  RunEventSummary,
  RunSummary,
} from "../lib/api";

type WorkbenchView =
  | "dashboard"
  | "agents"
  | "runs"
  | "approvals"
  | "knowledge"
  | "evals"
  | "settings";

type ApprovalDecision = "approved" | "rejected";

type ToolCallDetail = {
  id: string;
  runId: string;
  name: string;
  status: "succeeded" | "waiting_approval" | "failed";
  riskLevel: ApprovalSummary["riskLevel"];
  latencyMs: number | null;
  requiresApproval: boolean;
  inputSchema: string;
  resultPreview: string;
};

type ApprovalState = ApprovalSummary & {
  decision: ApprovalDecision | null;
  decidedAt: string | null;
};

type AgentSummary = {
  id: string;
  name: string;
  status: "online" | "idle" | "degraded";
  model: string;
  provider: string;
  activeRuns: number;
  queueDepth: number;
  tools: string[];
  memoryProfile: string;
  lastRun: string;
};

type DocumentIngestionSummary = {
  id: string;
  knowledgeBaseId: string;
  fileName: string;
  status: "indexed" | "chunking" | "embedding" | "failed";
  chunks: number;
  updatedAt: string;
  progress: number;
};

type EvalCaseSummary = {
  id: string;
  reportName: string;
  status: "passed" | "failed";
  scenario: string;
  expected: string;
  actual: string;
  latencyMs: number;
};

type SettingGroup = {
  title: string;
  items: {
    label: string;
    value: string;
    detail: string;
  }[];
};

type LiveRunLookupState = {
  status: "idle" | "loading" | "loaded" | "error";
  run: LiveRun | null;
  events: LiveRunEvent[];
  error: string | null;
};

type LiveApprovalState = {
  status: "loading" | "loaded" | "error";
  approvals: LiveApproval[];
  error: string | null;
  mutatingApprovalId: string | null;
};

type LiveKnowledgeBaseState = {
  status: "loading" | "loaded" | "error";
  knowledgeBases: LiveKnowledgeBase[];
  error: string | null;
};

type LiveRetrievalState = {
  status: "idle" | "loading" | "loaded" | "error";
  response: LiveRetrievalResponse | null;
  error: string | null;
};

const initialRuntimeHealth: RuntimeHealth = {
  state: "checking",
  service: "agent-kernel-api",
  status: "checking",
  baseUrl: "unknown",
  checkedAt: null,
  latencyMs: null,
};

const initialLiveRunLookup: LiveRunLookupState = {
  status: "idle",
  run: null,
  events: [],
  error: null,
};

const initialLiveApprovals: LiveApprovalState = {
  status: "loading",
  approvals: [],
  error: null,
  mutatingApprovalId: null,
};

const initialLiveKnowledgeBases: LiveKnowledgeBaseState = {
  status: "loading",
  knowledgeBases: [],
  error: null,
};

const initialLiveRetrieval: LiveRetrievalState = {
  status: "idle",
  response: null,
  error: null,
};

const navItems: { id: WorkbenchView; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "agents", label: "Agents" },
  { id: "runs", label: "Runs" },
  { id: "approvals", label: "Approvals" },
  { id: "knowledge", label: "Knowledge" },
  { id: "evals", label: "Evals" },
  { id: "settings", label: "Settings" },
];

const viewCopy: Record<WorkbenchView, { eyebrow: string; title: string; status: string }> = {
  dashboard: {
    eyebrow: "Production runtime",
    title: "Agent Workbench",
    status: "Public Alpha",
  },
  agents: {
    eyebrow: "Agent registry",
    title: "Agents",
    status: "Preview",
  },
  runs: {
    eyebrow: "Execution trace",
    title: "Runs",
    status: "Live lookup",
  },
  approvals: {
    eyebrow: "Human review",
    title: "Approvals",
    status: "Live + preview",
  },
  knowledge: {
    eyebrow: "RAG operations",
    title: "Knowledge",
    status: "Live retrieval",
  },
  evals: {
    eyebrow: "Quality gates",
    title: "Evals",
    status: "Report view",
  },
  settings: {
    eyebrow: "Runtime config",
    title: "Settings",
    status: "Read-only",
  },
};

const agents: AgentSummary[] = [
  {
    id: "research-agent",
    name: "Research Agent",
    status: "online",
    model: "mock:mock-small",
    provider: "mock",
    activeRuns: 1,
    queueDepth: 2,
    tools: ["kb_search", "memory_search", "external_write"],
    memoryProfile: "task + user preference",
    lastRun: "2 min ago",
  },
  {
    id: "ops-agent",
    name: "Ops Agent",
    status: "idle",
    model: "mock:mock-small",
    provider: "mock",
    activeRuns: 0,
    queueDepth: 0,
    tools: ["kb_search", "approval_request"],
    memoryProfile: "task scoped",
    lastRun: "11 min ago",
  },
  {
    id: "eval-agent",
    name: "Eval Agent",
    status: "degraded",
    model: "replay:baseline",
    provider: "replay",
    activeRuns: 0,
    queueDepth: 1,
    tools: ["rag_eval", "replay_lookup"],
    memoryProfile: "disabled",
    lastRun: "24 min ago",
  },
];

const runs: RunSummary[] = [
  {
    id: "run_9b1c",
    agentId: "research-agent",
    status: "waiting_approval",
    traceId: "9d4f1a6b0c2e47b48ddf8b176cba0c2f",
    task: "Summarize deployment rollback guidance",
    model: "mock:mock-small",
    latencyMs: 428,
    estimatedCost: 0,
    updatedAt: "2 min ago",
  },
  {
    id: "run_7e42",
    agentId: "ops-agent",
    status: "succeeded",
    traceId: "f23bfe128adc4f3cb4d29577ab7015a1",
    task: "Search release notes knowledge base",
    model: "mock:mock-small",
    latencyMs: 312,
    estimatedCost: 0,
    updatedAt: "11 min ago",
  },
  {
    id: "run_3a80",
    agentId: "eval-agent",
    status: "failed",
    traceId: "2c3cb98c3eb54f3db0a0a64d8d8d7f11",
    task: "Run RAG smoke regression",
    model: "replay:baseline",
    latencyMs: 91,
    estimatedCost: 0,
    updatedAt: "24 min ago",
  },
];

const timelinesByRun: Record<string, RunEventSummary[]> = {
  run_9b1c: [
    {
      sequence: 1,
      type: "run_created",
      status: "complete",
      label: "Run created",
      detail: "research-agent queued a rollback summary task",
    },
    {
      sequence: 2,
      type: "memory_retrieved",
      status: "complete",
      label: "Memory loaded",
      detail: "2 scoped memory items attached to model context",
    },
    {
      sequence: 3,
      type: "tool_call_requested",
      status: "complete",
      label: "Tool requested",
      detail: "kb_search requested top 5 chunks from Engineering Handbook",
    },
    {
      sequence: 4,
      type: "approval_requested",
      status: "waiting",
      label: "Approval waiting",
      detail: "external_write requires human approval before continuing",
    },
  ],
  run_7e42: [
    {
      sequence: 1,
      type: "run_started",
      status: "complete",
      label: "Run started",
      detail: "ops-agent started knowledge retrieval",
    },
    {
      sequence: 2,
      type: "tool_call_completed",
      status: "complete",
      label: "kb_search completed",
      detail: "Retrieved 3 cited chunks in 87ms",
    },
    {
      sequence: 3,
      type: "run_completed",
      status: "complete",
      label: "Run completed",
      detail: "Summary returned with cited retrieval result metadata",
    },
  ],
  run_3a80: [
    {
      sequence: 1,
      type: "run_started",
      status: "complete",
      label: "Eval started",
      detail: "Loaded rag-smoke dataset",
    },
    {
      sequence: 2,
      type: "model_call_retrying",
      status: "failed",
      label: "Replay lookup failed",
      detail: "No replay response registered for replay:baseline",
    },
    {
      sequence: 3,
      type: "run_failed",
      status: "failed",
      label: "Run failed",
      detail: "Deterministic replay fixture is missing",
    },
  ],
};

const toolCallsByRun: Record<string, ToolCallDetail[]> = {
  run_9b1c: [
    {
      id: "tool_902",
      runId: "run_9b1c",
      name: "kb_search",
      status: "succeeded",
      riskLevel: "read_only",
      latencyMs: 94,
      requiresApproval: false,
      inputSchema: "knowledge_base_id, query, top_k",
      resultPreview: "5 cited chunks from Engineering Handbook",
    },
    {
      id: "tool_944",
      runId: "run_9b1c",
      name: "external_write",
      status: "waiting_approval",
      riskLevel: "external_write",
      latencyMs: null,
      requiresApproval: true,
      inputSchema: "destination, title, content",
      resultPreview: "Waiting for approval before execution",
    },
  ],
  run_7e42: [
    {
      id: "tool_812",
      runId: "run_7e42",
      name: "kb_search",
      status: "succeeded",
      riskLevel: "read_only",
      latencyMs: 87,
      requiresApproval: false,
      inputSchema: "knowledge_base_id, query, top_k",
      resultPreview: "3 cited chunks from Release Notes",
    },
  ],
  run_3a80: [
    {
      id: "tool_701",
      runId: "run_3a80",
      name: "replay_lookup",
      status: "failed",
      riskLevel: "read_only",
      latencyMs: 12,
      requiresApproval: false,
      inputSchema: "model",
      resultPreview: "replay_not_found",
    },
  ],
};

const initialApprovals: ApprovalState[] = [
  {
    id: "appr_421",
    runId: "run_9b1c",
    toolName: "external_write",
    riskLevel: "external_write",
    reason: "Tool can write outside Agent Kernel state",
    requestedAt: "2 min ago",
    decision: null,
    decidedAt: null,
  },
  {
    id: "appr_317",
    runId: "run_6c10",
    toolName: "publish_report",
    riskLevel: "network",
    reason: "Network action requires operator review",
    requestedAt: "18 min ago",
    decision: null,
    decidedAt: null,
  },
];

const knowledgeBases: KnowledgeBaseSummary[] = [
  {
    id: "kb_platform",
    name: "Engineering Handbook",
    documents: 12,
    indexedChunks: 318,
    status: "active",
  },
  {
    id: "kb_release",
    name: "Release Notes",
    documents: 6,
    indexedChunks: 84,
    status: "indexing",
  },
];

const documentIngestions: DocumentIngestionSummary[] = [
  {
    id: "doc_118",
    knowledgeBaseId: "kb_platform",
    fileName: "rollback-playbook.md",
    status: "indexed",
    chunks: 42,
    updatedAt: "6 min ago",
    progress: 100,
  },
  {
    id: "doc_119",
    knowledgeBaseId: "kb_platform",
    fileName: "incident-handoff.md",
    status: "indexed",
    chunks: 37,
    updatedAt: "12 min ago",
    progress: 100,
  },
  {
    id: "doc_221",
    knowledgeBaseId: "kb_release",
    fileName: "2026-07-release-notes.md",
    status: "embedding",
    chunks: 19,
    updatedAt: "1 min ago",
    progress: 72,
  },
  {
    id: "doc_222",
    knowledgeBaseId: "kb_release",
    fileName: "migration-checklist.md",
    status: "chunking",
    chunks: 0,
    updatedAt: "now",
    progress: 31,
  },
];

const evalReports: EvalReportSummary[] = [
  {
    name: "rag-smoke",
    passed: true,
    passedCount: 3,
    failedCount: 0,
    caseCount: 3,
  },
  {
    name: "tool-regression",
    passed: false,
    passedCount: 7,
    failedCount: 1,
    caseCount: 8,
  },
];

const evalCases: EvalCaseSummary[] = [
  {
    id: "case_rag_001",
    reportName: "rag-smoke",
    status: "passed",
    scenario: "Return cited rollback guidance",
    expected: "At least one citation from Engineering Handbook",
    actual: "5 citations returned",
    latencyMs: 142,
  },
  {
    id: "case_rag_002",
    reportName: "rag-smoke",
    status: "passed",
    scenario: "Rank release note chunk first",
    expected: "Top result from Release Notes",
    actual: "Release Notes chunk ranked #1",
    latencyMs: 96,
  },
  {
    id: "case_tool_007",
    reportName: "tool-regression",
    status: "failed",
    scenario: "Replay lookup uses registered model",
    expected: "Replay response available",
    actual: "Replay fixture missing",
    latencyMs: 12,
  },
];

const settingGroups: SettingGroup[] = [
  {
    title: "Runtime",
    items: [
      {
        label: "API endpoint",
        value: "http://127.0.0.1:8000",
        detail: "NEXT_PUBLIC_AGENT_KERNEL_API_URL fallback",
      },
      {
        label: "Provider router",
        value: "mock + replay",
        detail: "Deterministic local providers for Web smoke work",
      },
      {
        label: "Metrics recorder",
        value: "in-memory",
        detail: "Local runtime metrics surface",
      },
    ],
  },
  {
    title: "Safety",
    items: [
      {
        label: "Approval mode",
        value: "local UI",
        detail: "No live approval mutation from the Web app yet",
      },
      {
        label: "Dangerous tools",
        value: "blocked",
        detail: "Policy engine remains server-side",
      },
      {
        label: "Network actions",
        value: "approval required",
        detail: "Human review before execution",
      },
    ],
  },
  {
    title: "Observability",
    items: [
      {
        label: "Trace IDs",
        value: "enabled",
        detail: "Run timeline uses deterministic trace identifiers",
      },
      {
        label: "Cost tracking",
        value: "enabled",
        detail: "Provider usage reports zero-cost local fixtures",
      },
      {
        label: "Eval reports",
        value: "visible",
        detail: "Regression result summaries are shown in Workbench",
      },
    ],
  },
];

export default function Home() {
  const [activeView, setActiveView] = useState<WorkbenchView>("dashboard");
  const [selectedRunId, setSelectedRunId] = useState(runs[0].id);
  const [selectedToolId, setSelectedToolId] = useState(toolCallsByRun[runs[0].id][0].id);
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState(knowledgeBases[0].id);
  const [selectedEvalName, setSelectedEvalName] = useState(evalReports[0].name);
  const [approvals, setApprovals] = useState(initialApprovals);
  const [runtimeHealth, setRuntimeHealth] = useState<RuntimeHealth>(initialRuntimeHealth);
  const [liveRunId, setLiveRunId] = useState("");
  const [liveRunLookup, setLiveRunLookup] =
    useState<LiveRunLookupState>(initialLiveRunLookup);
  const [liveApprovals, setLiveApprovals] =
    useState<LiveApprovalState>(initialLiveApprovals);
  const [liveKnowledgeBases, setLiveKnowledgeBases] =
    useState<LiveKnowledgeBaseState>(initialLiveKnowledgeBases);
  const [liveRetrievalKnowledgeBaseId, setLiveRetrievalKnowledgeBaseId] = useState("");
  const [liveRetrievalQuery, setLiveRetrievalQuery] = useState("");
  const [liveRetrieval, setLiveRetrieval] =
    useState<LiveRetrievalState>(initialLiveRetrieval);

  useEffect(() => {
    let ignore = false;

    async function loadLiveApprovals() {
      try {
        const response = await fetch("/api/agent-kernel/approvals", {
          headers: { accept: "application/json" },
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Approval list returned HTTP ${response.status}`);
        }

        const approvalsResponse = (await response.json()) as LiveApproval[];
        if (!ignore) {
          setLiveApprovals({
            status: "loaded",
            approvals: approvalsResponse,
            error: null,
            mutatingApprovalId: null,
          });
        }
      } catch (error) {
        if (!ignore) {
          setLiveApprovals({
            status: "error",
            approvals: [],
            error: error instanceof Error ? error.message : "Approval list lookup failed",
            mutatingApprovalId: null,
          });
        }
      }
    }

    void loadLiveApprovals();

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    let ignore = false;

    async function loadLiveKnowledgeBases() {
      try {
        const response = await fetch("/api/agent-kernel/knowledge-bases", {
          headers: { accept: "application/json" },
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Knowledge base list returned HTTP ${response.status}`);
        }

        const knowledgeBasesResponse = (await response.json()) as LiveKnowledgeBase[];
        if (!ignore) {
          setLiveKnowledgeBases({
            status: "loaded",
            knowledgeBases: knowledgeBasesResponse,
            error: null,
          });
        }
      } catch (error) {
        if (!ignore) {
          setLiveKnowledgeBases({
            status: "error",
            knowledgeBases: [],
            error:
              error instanceof Error ? error.message : "Knowledge base list lookup failed",
          });
        }
      }
    }

    void loadLiveKnowledgeBases();

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    let ignore = false;

    async function loadRuntimeHealth() {
      try {
        const response = await fetch("/api/agent-kernel/health", {
          headers: { accept: "application/json" },
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Health proxy returned HTTP ${response.status}`);
        }

        const health = (await response.json()) as RuntimeHealth;
        if (!ignore) {
          setRuntimeHealth(health);
        }
      } catch (error) {
        if (!ignore) {
          setRuntimeHealth({
            ...initialRuntimeHealth,
            state: "offline",
            status: "unreachable",
            error: error instanceof Error ? error.message : "Health check failed",
          });
        }
      }
    }

    void loadRuntimeHealth();

    return () => {
      ignore = true;
    };
  }, []);

  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0];
  const selectedTimeline = timelinesByRun[selectedRun.id] ?? [];
  const selectedToolCalls = toolCallsByRun[selectedRun.id] ?? [];
  const selectedTool =
    selectedToolCalls.find((toolCall) => toolCall.id === selectedToolId) ??
    selectedToolCalls[0] ??
    null;
  const selectedKnowledgeBase =
    knowledgeBases.find((knowledgeBase) => knowledgeBase.id === selectedKnowledgeBaseId) ??
    knowledgeBases[0];
  const selectedDocuments = documentIngestions.filter(
    (document) => document.knowledgeBaseId === selectedKnowledgeBase.id,
  );
  const selectedEval =
    evalReports.find((report) => report.name === selectedEvalName) ?? evalReports[0];
  const selectedEvalCases = evalCases.filter((evalCase) => evalCase.reportName === selectedEval.name);

  const pendingApprovals = approvals.filter((approval) => approval.decision === null);
  const approvalHistory = useMemo(
    () => approvals.filter((approval) => approval.decision !== null),
    [approvals],
  );
  const metrics = [
    { label: "Active runs", value: `${runs.length}`, detail: "1 waiting approval" },
    {
      label: "Pending approvals",
      value: `${pendingApprovals.length}`,
      detail: "preview inbox plus live status",
    },
    {
      label: "Indexed chunks",
      value: `${knowledgeBases.reduce((total, kb) => total + kb.indexedChunks, 0)}`,
      detail: `${knowledgeBases.length} knowledge bases`,
    },
    { label: "Eval pass rate", value: "91%", detail: "10 of 11 cases" },
  ];

  function selectRun(runId: string) {
    setSelectedRunId(runId);
    setSelectedToolId(toolCallsByRun[runId]?.[0]?.id ?? "");
  }

  function decideApproval(approvalId: string, decision: ApprovalDecision) {
    setApprovals((currentApprovals) =>
      currentApprovals.map((approval) =>
        approval.id === approvalId
          ? {
              ...approval,
              decision,
              decidedAt: "just now",
            }
          : approval,
      ),
    );
  }

  async function lookupLiveRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const runId = liveRunId.trim();
    if (runId.length === 0) {
      setLiveRunLookup({
        ...initialLiveRunLookup,
        status: "error",
        error: "Enter a run ID first.",
      });
      return;
    }

    setLiveRunLookup({
      ...initialLiveRunLookup,
      status: "loading",
    });

    try {
      const [runResponse, eventsResponse] = await Promise.all([
        fetch(`/api/agent-kernel/runs/${encodeURIComponent(runId)}`, {
          headers: { accept: "application/json" },
          cache: "no-store",
        }),
        fetch(`/api/agent-kernel/runs/${encodeURIComponent(runId)}/events`, {
          headers: { accept: "application/json" },
          cache: "no-store",
        }),
      ]);

      if (!runResponse.ok) {
        throw new Error(`Run lookup returned HTTP ${runResponse.status}`);
      }

      if (!eventsResponse.ok) {
        throw new Error(`Run events lookup returned HTTP ${eventsResponse.status}`);
      }

      const [run, events] = (await Promise.all([
        runResponse.json(),
        eventsResponse.json(),
      ])) as [LiveRun, LiveRunEvent[]];

      setLiveRunLookup({
        status: "loaded",
        run,
        events,
        error: null,
      });
    } catch (error) {
      setLiveRunLookup({
        ...initialLiveRunLookup,
        status: "error",
        error: error instanceof Error ? error.message : "Run lookup failed",
      });
    }
  }

  async function decideLiveApproval(approvalId: string, decision: ApprovalDecision) {
    const action = decision === "approved" ? "approve" : "reject";

    setLiveApprovals((current) => ({
      ...current,
      error: null,
      mutatingApprovalId: approvalId,
    }));

    try {
      const response = await fetch(`/api/agent-kernel/approvals/${approvalId}/${action}`, {
        body:
          decision === "approved"
            ? JSON.stringify({ decision_note: "Approved from Workbench" })
            : JSON.stringify({ reason: "Rejected from Workbench" }),
        headers: {
          accept: "application/json",
          "content-type": "application/json",
        },
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`Live approval ${decision} returned HTTP ${response.status}`);
      }

      const updatedApproval = (await response.json()) as LiveApproval;
      setLiveApprovals((current) => ({
        ...current,
        status: "loaded",
        approvals: current.approvals.map((approval) =>
          approval.id === updatedApproval.id ? updatedApproval : approval,
        ),
        error: null,
        mutatingApprovalId: null,
      }));
    } catch (error) {
      setLiveApprovals((current) => ({
        ...current,
        status: current.status === "loading" ? "error" : current.status,
        error: error instanceof Error ? error.message : "Live approval mutation failed",
        mutatingApprovalId: null,
      }));
    }
  }

  async function searchLiveKnowledgeBase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const knowledgeBaseId = liveRetrievalKnowledgeBaseId.trim();
    const query = liveRetrievalQuery.trim();

    if (knowledgeBaseId.length === 0 || query.length === 0) {
      setLiveRetrieval({
        ...initialLiveRetrieval,
        status: "error",
        error: "Enter a knowledge base ID and search query first.",
      });
      return;
    }

    setLiveRetrieval({
      ...initialLiveRetrieval,
      status: "loading",
    });

    try {
      const response = await fetch(
        `/api/agent-kernel/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/retrieve`,
        {
          body: JSON.stringify({ query, top_k: 5 }),
          headers: {
            accept: "application/json",
            "content-type": "application/json",
          },
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new Error(`Knowledge retrieval returned HTTP ${response.status}`);
      }

      const retrievalResponse = (await response.json()) as LiveRetrievalResponse;
      setLiveRetrieval({
        status: "loaded",
        response: retrievalResponse,
        error: null,
      });
    } catch (error) {
      setLiveRetrieval({
        ...initialLiveRetrieval,
        status: "error",
        error: error instanceof Error ? error.message : "Knowledge retrieval failed",
      });
    }
  }

  return (
    <main className="workbench-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">AK</div>
          <div>
            <div className="brand">Agent Kernel</div>
            <div className="brand-subtitle">Workbench</div>
          </div>
        </div>
        <nav className="nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <button
              className={item.id === activeView ? "nav-item active" : "nav-item"}
              key={item.id}
              onClick={() => setActiveView(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">{viewCopy[activeView].eyebrow}</p>
            <h1>{viewCopy[activeView].title}</h1>
          </div>
          <div className={`runtime-status ${runtimeHealth.state}`} aria-label="Runtime status">
            <span className={`status-dot ${runtimeHealth.state}`} />
            <span>{runtimeStatusLabel(runtimeHealth)}</span>
            <small>{viewCopy[activeView].status}</small>
          </div>
        </header>

        <section className="metric-grid" aria-label="Dashboard metrics">
          {metrics.map((metric) => (
            <article className="metric-card" key={metric.label}>
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
              <small>{metric.detail}</small>
            </article>
          ))}
        </section>

        {renderWorkbenchScopeBanner()}

        <section className="workspace-view">{renderActiveView()}</section>
      </section>
    </main>
  );

  function renderWorkbenchScopeBanner() {
    return (
      <section className="scope-banner" aria-label="Workbench data scope">
        <div>
          <span className="signal-badge">Public Alpha</span>
          <strong>Live where it matters for first-run verification.</strong>
          <p>
            Health, run lookup, approvals, knowledge bases, and retrieval search call the
            backend API. Agent cards, list previews, document ingestion, and eval summaries
            remain preview data until their live list endpoints are complete.
          </p>
        </div>
        <code>API: {runtimeHealth.baseUrl}</code>
      </section>
    );
  }

  function renderActiveView() {
    if (activeView === "agents") {
      return (
        <section className="agent-grid">
          {agents.map((agent) => (
            <article className="agent-card" key={agent.id}>
              <div className="agent-card-header">
                <div>
                  <p className="eyebrow">{agent.id}</p>
                  <h2>{agent.name}</h2>
                </div>
                <HealthBadge status={agent.status} />
              </div>
              <dl className="agent-meta-grid">
                <div>
                  <dt>Provider</dt>
                  <dd>{agent.provider}</dd>
                </div>
                <div>
                  <dt>Model</dt>
                  <dd>{agent.model}</dd>
                </div>
                <div>
                  <dt>Active runs</dt>
                  <dd>{agent.activeRuns}</dd>
                </div>
                <div>
                  <dt>Queue</dt>
                  <dd>{agent.queueDepth}</dd>
                </div>
                <div>
                  <dt>Memory</dt>
                  <dd>{agent.memoryProfile}</dd>
                </div>
                <div>
                  <dt>Last run</dt>
                  <dd>{agent.lastRun}</dd>
                </div>
              </dl>
              <div className="capability-list" aria-label={`${agent.name} tools`}>
                {agent.tools.map((tool) => (
                  <code key={tool}>{tool}</code>
                ))}
              </div>
            </article>
          ))}
        </section>
      );
    }

    if (activeView === "runs") {
      return (
        <>
          <section className="single-grid">{renderLiveRunLookup()}</section>
          <section className="main-grid">{renderRunList()}{renderTimeline()}</section>
          <section className="single-grid">{renderToolDetail()}</section>
        </>
      );
    }

    if (activeView === "approvals") {
      return (
        <section className="detail-grid">
          {renderApprovalInbox()}
          {renderDecisionHistory()}
        </section>
      );
    }

    if (activeView === "knowledge") {
      return (
        <>
          <section className="single-grid">{renderLiveKnowledgeBases()}</section>
          <section className="single-grid">{renderLiveRetrievalSearch()}</section>
          <section className="split-grid">{renderKnowledgeIndexList()}{renderDocumentIngestion()}</section>
        </>
      );
    }

    if (activeView === "evals") {
      return (
        <section className="split-grid">
          <section className="panel" aria-labelledby="eval-report-heading">
            <div className="section-header">
              <div>
                <p className="eyebrow">Reports</p>
                <h2 id="eval-report-heading">Regression runs</h2>
              </div>
              <span className="count-pill">{evalReports.length}</span>
            </div>
            <div className="eval-report-grid">
              {evalReports.map((report) => (
                <button
                  className={report.name === selectedEval.name ? "eval-report-card selected" : "eval-report-card"}
                  key={report.name}
                  onClick={() => setSelectedEvalName(report.name)}
                  type="button"
                >
                  <div>
                    <strong>{report.name}</strong>
                    <p>
                      {report.passedCount}/{report.caseCount} passed
                    </p>
                  </div>
                  <span className={report.passed ? "eval-pass" : "eval-fail"}>
                    {report.passed ? "passed" : `${report.failedCount} failed`}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="panel" aria-labelledby="eval-case-heading">
            <div className="section-header">
              <div>
                <p className="eyebrow">{selectedEval.name}</p>
                <h2 id="eval-case-heading">Behavior cases</h2>
              </div>
              <span className={selectedEval.passed ? "eval-pass" : "eval-fail"}>
                {selectedEval.passed ? "passed" : `${selectedEval.failedCount} failed`}
              </span>
            </div>
            <div className="case-list">
              {selectedEvalCases.map((evalCase) => (
                <article className="case-item" key={evalCase.id}>
                  <div>
                    <strong>{evalCase.scenario}</strong>
                    <p>Expected: {evalCase.expected}</p>
                    <p>Actual: {evalCase.actual}</p>
                  </div>
                  <div className="case-side">
                    <CaseBadge status={evalCase.status} />
                    <span>{evalCase.latencyMs}ms</span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </section>
      );
    }

    if (activeView === "settings") {
      return (
        <section className="settings-grid">
          {settingGroups.map((group) => (
            <section className="panel setting-panel" aria-labelledby={`${group.title}-heading`} key={group.title}>
              <div className="section-header compact">
                <h2 id={`${group.title}-heading`}>{group.title}</h2>
                <span className="signal-badge">read only</span>
              </div>
              <dl className="settings-list expanded">
                {group.items.map((item) => (
                  <div key={item.label}>
                    <dt>{item.label}</dt>
                    <dd>
                      <strong>{item.value}</strong>
                      <span>{item.detail}</span>
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </section>
      );
    }

    return (
      <>
        <section className="single-grid">{renderLiveRunLookup()}</section>
        <section className="main-grid">{renderRunList()}{renderTimeline()}</section>
        <section className="detail-grid">{renderToolDetail()}{renderApprovalInbox()}</section>
        <section className="lower-grid">
          {renderDecisionHistory()}
          {renderKnowledgeSummary()}
          {renderEvalSummary()}
          {renderSettingsSummary()}
        </section>
      </>
    );
  }

  function renderLiveRunLookup() {
    const isLoading = liveRunLookup.status === "loading";

    return (
      <section className="panel live-run-panel" aria-labelledby="live-run-heading">
        <div className="section-header">
          <div>
            <p className="eyebrow">Live API</p>
            <h2 id="live-run-heading">Run lookup</h2>
          </div>
          <span className="signal-badge">live</span>
        </div>

        <form className="lookup-form" onSubmit={lookupLiveRun}>
          <label htmlFor="live-run-id">Run ID</label>
          <input
            id="live-run-id"
            onChange={(event) => setLiveRunId(event.target.value)}
            placeholder="Paste a UUID from agent-kernel run create"
            type="text"
            value={liveRunId}
          />
          <button className="secondary-action" disabled={isLoading} type="submit">
            {isLoading ? "Looking up" : "Lookup"}
          </button>
        </form>

        <p className="local-note">
          This lookup calls the real Agent Kernel API through the Web app. The run list below is
          still fixture-backed until the backend exposes a list-runs endpoint.
        </p>

        {liveRunLookup.status === "error" ? (
          <LiveError message={liveRunLookup.error} />
        ) : null}

        {liveRunLookup.run === null ? null : (
          <div className="live-run-result">
            <dl className="live-run-meta">
              <div>
                <dt>Status</dt>
                <dd>
                  <StatusBadge status={liveRunLookup.run.status} />
                </dd>
              </div>
              <div>
                <dt>Agent</dt>
                <dd>{liveRunLookup.run.agent_id}</dd>
              </div>
              <div>
                <dt>Trace</dt>
                <dd>{liveRunLookup.run.trace_id ?? "none"}</dd>
              </div>
              <div>
                <dt>Cost</dt>
                <dd>${liveRunLookup.run.estimated_cost_total.toFixed(6)}</dd>
              </div>
            </dl>

            <ol className="timeline live-timeline" aria-label="Live run timeline">
              {liveRunLookup.events.map((event) => (
                <li className="timeline-item complete" key={event.id}>
                  <span className="timeline-index">{event.sequence}</span>
                  <div>
                    <strong>{event.type}</strong>
                    <p>{event.created_at}</p>
                    <code>{eventSummary(event.payload)}</code>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}
      </section>
    );
  }

  function renderLiveKnowledgeBases() {
    return (
      <section className="panel live-kb-panel" aria-labelledby="live-kb-heading">
        <div className="section-header">
          <div>
            <p className="eyebrow">Live API</p>
            <h2 id="live-kb-heading">Knowledge base list</h2>
          </div>
          <span className="signal-badge">live</span>
        </div>
        <div
          className={`live-api-strip ${liveKnowledgeBases.status}`}
          aria-label="Live knowledge bases status"
        >
          <span className={`status-dot ${liveKnowledgeBases.status === "loaded" ? "online" : "checking"}`} />
          <strong>{liveKnowledgeBaseStatusText(liveKnowledgeBases)}</strong>
        </div>
        {liveKnowledgeBases.status === "loaded" && liveKnowledgeBases.knowledgeBases.length > 0 ? (
          <div className="live-kb-list" aria-label="Live knowledge bases">
            {liveKnowledgeBases.knowledgeBases.map((knowledgeBase) => (
              <article className="live-kb-item" key={knowledgeBase.id}>
                <div>
                  <strong>{knowledgeBase.name}</strong>
                  <p>{knowledgeBase.description || "No description"}</p>
                  <span>
                    {knowledgeBase.id} · updated {knowledgeBase.updated_at}
                  </span>
                </div>
                <button
                  className="secondary-action compact-action"
                  onClick={() => setLiveRetrievalKnowledgeBaseId(knowledgeBase.id)}
                  type="button"
                >
                  Use for search
                </button>
                <span className={`kb-status ${knowledgeBase.status}`}>
                  {knowledgeBase.status}
                </span>
              </article>
            ))}
          </div>
        ) : null}
        {liveKnowledgeBases.error ? (
          <LiveError message={liveKnowledgeBases.error} />
        ) : null}
      </section>
    );
  }

  function renderLiveRetrievalSearch() {
    const isLoading = liveRetrieval.status === "loading";

    return (
      <section className="panel live-retrieval-panel" aria-labelledby="live-retrieval-heading">
        <div className="section-header">
          <div>
            <p className="eyebrow">Live API</p>
            <h2 id="live-retrieval-heading">Retrieval search</h2>
          </div>
          <span className="signal-badge">live</span>
        </div>

        <form className="retrieval-form" onSubmit={searchLiveKnowledgeBase}>
          <label htmlFor="live-retrieval-kb-id">Knowledge base ID</label>
          <input
            id="live-retrieval-kb-id"
            onChange={(event) => setLiveRetrievalKnowledgeBaseId(event.target.value)}
            placeholder="Paste a knowledge base UUID"
            type="text"
            value={liveRetrievalKnowledgeBaseId}
          />
          <label htmlFor="live-retrieval-query">Search query</label>
          <input
            id="live-retrieval-query"
            onChange={(event) => setLiveRetrievalQuery(event.target.value)}
            placeholder="Search indexed chunks"
            type="text"
            value={liveRetrievalQuery}
          />
          <button className="secondary-action" disabled={isLoading} type="submit">
            {isLoading ? "Searching" : "Search live"}
          </button>
        </form>

        <p className="local-note">
          This search calls the real retrieval API and shows raw cited chunks. Final answer
          synthesis remains a later agent-runtime concern.
        </p>

        {liveRetrieval.status === "error" ? (
          <LiveError message={liveRetrieval.error} />
        ) : null}

        {liveRetrieval.response === null ? null : (
          <div className="retrieval-results" aria-label="Live retrieval results">
            <div className="retrieval-summary">
              <strong>{liveRetrieval.response.results.length} results</strong>
              <span>
                {liveRetrieval.response.model} · {liveRetrieval.response.query}
              </span>
            </div>
            {liveRetrieval.response.results.length === 0 ? (
              <p className="empty-state">No chunks matched this query.</p>
            ) : (
              liveRetrieval.response.results.map((result) => (
                <article className="retrieval-result" key={result.citation.chunk_id}>
                  <div>
                    <strong>{result.citation.document_title}</strong>
                    <p>{result.content}</p>
                    <span>
                      chunk {result.citation.chunk_index} · score {result.score.toFixed(3)}
                    </span>
                  </div>
                  <code>{result.citation.document_source_uri}</code>
                </article>
              ))
            )}
          </div>
        )}
      </section>
    );
  }

  function renderKnowledgeIndexList() {
    return (
      <section className="panel" aria-labelledby="knowledge-list-heading">
        <div className="section-header">
          <div>
            <p className="eyebrow">Fixture preview</p>
            <h2 id="knowledge-list-heading">Indexes</h2>
          </div>
          <span className="count-pill">{knowledgeBases.length}</span>
        </div>
        <div className="knowledge-list">
          {knowledgeBases.map((knowledgeBase) => (
            <button
              className={
                knowledgeBase.id === selectedKnowledgeBase.id ? "kb-row selected" : "kb-row"
              }
              key={knowledgeBase.id}
              onClick={() => setSelectedKnowledgeBaseId(knowledgeBase.id)}
              type="button"
            >
              <div>
                <strong>{knowledgeBase.name}</strong>
                <p>
                  {knowledgeBase.documents} docs · {knowledgeBase.indexedChunks} chunks
                </p>
              </div>
              <span className={`kb-status ${knowledgeBase.status}`}>
                {knowledgeBase.status}
              </span>
            </button>
          ))}
        </div>
      </section>
    );
  }

  function renderDocumentIngestion() {
    return (
      <section className="panel" aria-labelledby="document-ingestion-heading">
        <div className="section-header">
          <div>
            <p className="eyebrow">{selectedKnowledgeBase.id}</p>
            <h2 id="document-ingestion-heading">Document ingestion</h2>
          </div>
          <span className="count-pill">{selectedDocuments.length}</span>
        </div>
        <div className="document-list">
          {selectedDocuments.map((document) => (
            <article className="document-item" key={document.id}>
              <div>
                <strong>{document.fileName}</strong>
                <p>
                  {document.id} · {document.chunks} chunks · {document.updatedAt}
                </p>
              </div>
              <div className="doc-progress">
                <IngestionBadge status={document.status} />
                <div className="progress-bar" aria-label={`${document.fileName} progress`}>
                  <span style={{ width: `${document.progress}%` }} />
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderRunList() {
    return (
      <section className="panel runs-panel" aria-labelledby="runs-heading">
        <div className="section-header">
          <div>
            <p className="eyebrow">Runs</p>
            <h2 id="runs-heading">Execution queue</h2>
          </div>
          <button className="secondary-action" type="button">
            Refresh
          </button>
        </div>
        <div className="run-list">
          {runs.map((run) => (
            <button
              className={run.id === selectedRun.id ? "run-row selected" : "run-row"}
              key={run.id}
              onClick={() => selectRun(run.id)}
              type="button"
            >
              <div>
                <div className="row-title">{run.task}</div>
                <div className="row-meta">
                  {run.id} · {run.agentId} · {run.model}
                </div>
              </div>
              <div className="row-side">
                <StatusBadge status={run.status} />
                <span>{run.updatedAt}</span>
              </div>
            </button>
          ))}
        </div>
      </section>
    );
  }

  function renderTimeline() {
    return (
      <section className="panel timeline-panel" aria-labelledby="timeline-heading">
        <div className="section-header">
          <div>
            <p className="eyebrow">Trace</p>
            <h2 id="timeline-heading">{selectedRun.id}</h2>
          </div>
          <code>{selectedRun.traceId.slice(0, 12)}</code>
        </div>
        <ol className="timeline">
          {selectedTimeline.map((event) => (
            <li className={`timeline-item ${event.status}`} key={event.sequence}>
              <span className="timeline-index">{event.sequence}</span>
              <div>
                <strong>{event.label}</strong>
                <p>{event.detail}</p>
                <code>{event.type}</code>
              </div>
            </li>
          ))}
        </ol>
      </section>
    );
  }

  function renderToolDetail() {
    return (
      <section className="panel" aria-labelledby="tool-heading">
        <div className="section-header compact">
          <h2 id="tool-heading">Tool call detail</h2>
          <span className="count-pill">{selectedToolCalls.length}</span>
        </div>
        <div className="tool-layout">
          <div className="tool-list">
            {selectedToolCalls.map((toolCall) => (
              <button
                className={selectedTool?.id === toolCall.id ? "tool-row selected" : "tool-row"}
                key={toolCall.id}
                onClick={() => setSelectedToolId(toolCall.id)}
                type="button"
              >
                <span>{toolCall.name}</span>
                <StatusBadge status={toolCall.status} />
              </button>
            ))}
          </div>
          {selectedTool ? (
            <dl className="tool-detail">
              <div>
                <dt>Tool call ID</dt>
                <dd>{selectedTool.id}</dd>
              </div>
              <div>
                <dt>Risk</dt>
                <dd>
                  <RiskBadge risk={selectedTool.riskLevel} />
                </dd>
              </div>
              <div>
                <dt>Latency</dt>
                <dd>{selectedTool.latencyMs === null ? "pending" : `${selectedTool.latencyMs}ms`}</dd>
              </div>
              <div>
                <dt>Input schema</dt>
                <dd>{selectedTool.inputSchema}</dd>
              </div>
              <div>
                <dt>Result</dt>
                <dd>{selectedTool.resultPreview}</dd>
              </div>
            </dl>
          ) : (
            <p className="empty-state">No tool calls recorded for this run.</p>
          )}
        </div>
      </section>
    );
  }

  function renderApprovalInbox() {
    return (
      <section className="panel" aria-labelledby="approvals-heading">
        <div className="section-header compact">
          <h2 id="approvals-heading">Approval inbox</h2>
          <span className="count-pill">{pendingApprovals.length}</span>
        </div>
        <div className={`live-api-strip ${liveApprovals.status}`} aria-label="Live approvals status">
          <span className={`status-dot ${liveApprovals.status === "loaded" ? "online" : "checking"}`} />
          <strong>{liveApprovalStatusText(liveApprovals)}</strong>
        </div>
        {liveApprovals.status === "loaded" && liveApprovals.approvals.length > 0 ? (
          <div className="live-approval-list" aria-label="Live approvals">
            {liveApprovals.approvals.slice(0, 4).map((approval) => (
              <article className="live-approval-item" key={approval.id}>
                <div>
                  <strong>{approval.status}</strong>
                  <p>{approval.reason}</p>
                  <span>
                    {approval.run_id} · {approval.requested_at}
                  </span>
                </div>
                <div className="live-approval-actions">
                  <code>{approval.tool_call_id}</code>
                  {approval.status === "requested" ? (
                    <div className="button-pair">
                      <button
                        disabled={liveApprovals.mutatingApprovalId === approval.id}
                        onClick={() => decideLiveApproval(approval.id, "approved")}
                        type="button"
                      >
                        Approve live
                      </button>
                      <button
                        disabled={liveApprovals.mutatingApprovalId === approval.id}
                        onClick={() => decideLiveApproval(approval.id, "rejected")}
                        type="button"
                      >
                        Reject live
                      </button>
                    </div>
                  ) : (
                    <span className={`decision-pill ${approval.status}`}>
                      {approval.status} · {approval.resolved_at ?? "pending sync"}
                    </span>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : null}
        {liveApprovals.error ? (
          <LiveError message={liveApprovals.error} />
        ) : null}
        <p className="local-note">
          Live approvals appear above. The approval cards below are preview data for
          first-run UI coverage.
        </p>
        <div className="stack">
          {approvals.map((approval) => (
            <article className="approval-item" key={approval.id}>
              <div>
                <strong>{approval.toolName}</strong>
                <p>{approval.reason}</p>
                <span>
                  {approval.runId} · {approval.requestedAt}
                </span>
              </div>
              <div className="approval-actions">
                <RiskBadge risk={approval.riskLevel} />
                {approval.decision ? (
                  <span className={`decision-pill ${approval.decision}`}>
                    {approval.decision} · {approval.decidedAt}
                  </span>
                ) : (
                  <div className="button-pair">
                    <button onClick={() => decideApproval(approval.id, "approved")} type="button">
                      Approve
                    </button>
                    <button onClick={() => decideApproval(approval.id, "rejected")} type="button">
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderDecisionHistory() {
    return (
      <section className="panel" aria-labelledby="history-heading">
        <div className="section-header compact">
          <h2 id="history-heading">Decision history</h2>
          <span className="count-pill">{approvalHistory.length}</span>
        </div>
        {approvalHistory.length > 0 ? (
          <div className="stack">
            {approvalHistory.map((approval) => (
              <article className="history-item" key={approval.id}>
                <strong>{approval.id}</strong>
                <span className={`decision-pill ${approval.decision ?? ""}`}>
                  {approval.decision}
                </span>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">No local approval decisions yet.</p>
        )}
      </section>
    );
  }

  function renderKnowledgeSummary() {
    return (
      <section className="panel" aria-labelledby="knowledge-heading">
        <div className="section-header compact">
          <h2 id="knowledge-heading">Knowledge bases</h2>
          <span className="count-pill">{knowledgeBases.length}</span>
        </div>
        <div className="stack">
          {knowledgeBases.map((kb) => (
            <article className="kb-item" key={kb.id}>
              <div>
                <strong>{kb.name}</strong>
                <p>
                  {kb.documents} docs · {kb.indexedChunks} chunks
                </p>
              </div>
              <span className={`kb-status ${kb.status}`}>{kb.status}</span>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderEvalSummary() {
    return (
      <section className="panel" aria-labelledby="evals-heading">
        <div className="section-header compact">
          <h2 id="evals-heading">Eval reports</h2>
          <span className="count-pill">{evalReports.length}</span>
        </div>
        <div className="stack">
          {evalReports.map((report) => (
            <article className="eval-item" key={report.name}>
              <div>
                <strong>{report.name}</strong>
                <p>
                  {report.passedCount}/{report.caseCount} passed
                </p>
              </div>
              <span className={report.passed ? "eval-pass" : "eval-fail"}>
                {report.passed ? "passed" : `${report.failedCount} failed`}
              </span>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderSettingsSummary() {
    return (
      <section className="panel" aria-labelledby="settings-heading">
        <div className="section-header compact">
          <h2 id="settings-heading">Runtime settings</h2>
        </div>
        <dl className="settings-list">
          <div>
            <dt>Provider router</dt>
            <dd>mock + replay</dd>
          </div>
          <div>
            <dt>Metrics recorder</dt>
            <dd>in-memory</dd>
          </div>
          <div>
            <dt>Approval mode</dt>
            <dd>local UI</dd>
          </div>
        </dl>
      </section>
    );
  }
}

function runtimeStatusLabel(health: RuntimeHealth) {
  if (health.state === "checking") {
    return "Checking API";
  }

  if (health.state === "online") {
    const latency = health.latencyMs === null ? "" : ` · ${health.latencyMs}ms`;
    return `API reachable${latency}`;
  }

  return "API unreachable";
}

function eventSummary(payload: Record<string, unknown>) {
  const entries = Object.entries(payload);
  if (entries.length === 0) {
    return "{}";
  }

  return JSON.stringify(Object.fromEntries(entries.slice(0, 3)));
}

function liveApprovalStatusText(state: LiveApprovalState) {
  if (state.status === "loading") {
    return "Loading live approvals";
  }

  if (state.status === "loaded") {
    return `${state.approvals.length} live approvals from API`;
  }

  return state.error ?? "Live approvals unavailable";
}

function liveKnowledgeBaseStatusText(state: LiveKnowledgeBaseState) {
  if (state.status === "loading") {
    return "Loading live knowledge bases";
  }

  if (state.status === "loaded") {
    return `${state.knowledgeBases.length} live knowledge bases from API`;
  }

  return state.error ?? "Live knowledge bases unavailable";
}

function LiveError({ message }: { message: string | null }) {
  return (
    <div className="lookup-error" role="status">
      <strong>{message ?? "Live API request failed."}</strong>
      <span>
        Start `uv run agent-kernel-api`, verify `/healthz`, then refresh the Workbench.
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: RunSummary["status"] | ToolCallDetail["status"] }) {
  return <span className={`status-badge ${status}`}>{status.replace("_", " ")}</span>;
}

function RiskBadge({ risk }: { risk: ApprovalSummary["riskLevel"] }) {
  return <span className={`risk-badge ${risk}`}>{risk.replace("_", " ")}</span>;
}

function HealthBadge({ status }: { status: AgentSummary["status"] }) {
  return <span className={`health-badge ${status}`}>{status}</span>;
}

function IngestionBadge({ status }: { status: DocumentIngestionSummary["status"] }) {
  return <span className={`ingestion-badge ${status}`}>{status}</span>;
}

function CaseBadge({ status }: { status: EvalCaseSummary["status"] }) {
  return <span className={`case-badge ${status}`}>{status}</span>;
}
