"use client";

import { useMemo, useState } from "react";

import type {
  ApprovalSummary,
  EvalReportSummary,
  KnowledgeBaseSummary,
  RunEventSummary,
  RunSummary,
} from "../lib/api";

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

const navItems = [
  { label: "Dashboard", active: true },
  { label: "Agents", active: false },
  { label: "Runs", active: false },
  { label: "Approvals", active: false },
  { label: "Knowledge", active: false },
  { label: "Evals", active: false },
  { label: "Settings", active: false },
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

const metrics = [
  { label: "Active runs", value: "3", detail: "1 waiting approval" },
  { label: "Pending approvals", value: "2", detail: "local decisions only" },
  { label: "Indexed chunks", value: "402", detail: "2 knowledge bases" },
  { label: "Eval pass rate", value: "91%", detail: "10 of 11 cases" },
];

export default function Home() {
  const [selectedRunId, setSelectedRunId] = useState(runs[0].id);
  const [selectedToolId, setSelectedToolId] = useState(toolCallsByRun[runs[0].id][0].id);
  const [approvals, setApprovals] = useState(initialApprovals);

  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0];
  const selectedTimeline = timelinesByRun[selectedRun.id] ?? [];
  const selectedToolCalls = toolCallsByRun[selectedRun.id] ?? [];
  const selectedTool =
    selectedToolCalls.find((toolCall) => toolCall.id === selectedToolId) ??
    selectedToolCalls[0] ??
    null;

  const approvalHistory = useMemo(
    () => approvals.filter((approval) => approval.decision !== null),
    [approvals],
  );

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
            <button className={item.active ? "nav-item active" : "nav-item"} key={item.label}>
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Production runtime</p>
            <h1>Agent Workbench</h1>
          </div>
          <div className="runtime-status" aria-label="Runtime status">
            <span className="status-dot" />
            Local UI state
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

        <section className="main-grid">
          <section className="panel runs-panel" aria-labelledby="runs-heading">
            <div className="section-header">
              <div>
                <p className="eyebrow">Runs</p>
                <h2 id="runs-heading">Execution queue</h2>
              </div>
              <button className="secondary-action">Refresh</button>
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
        </section>

        <section className="detail-grid">
          <section className="panel" aria-labelledby="tool-heading">
            <div className="section-header compact">
              <h2 id="tool-heading">Tool call detail</h2>
              <span className="count-pill">{selectedToolCalls.length}</span>
            </div>
            <div className="tool-layout">
              <div className="tool-list">
                {selectedToolCalls.map((toolCall) => (
                  <button
                    className={
                      selectedTool?.id === toolCall.id ? "tool-row selected" : "tool-row"
                    }
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
                    <dd>
                      {selectedTool.latencyMs === null ? "pending" : `${selectedTool.latencyMs}ms`}
                    </dd>
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

          <section className="panel" aria-labelledby="approvals-heading">
            <div className="section-header compact">
              <h2 id="approvals-heading">Approval inbox</h2>
              <span className="count-pill">
                {approvals.filter((approval) => !approval.decision).length}
              </span>
            </div>
            <p className="local-note">Decisions here are local UI state for Day 31.</p>
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
                        <button
                          onClick={() => decideApproval(approval.id, "approved")}
                          type="button"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => decideApproval(approval.id, "rejected")}
                          type="button"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </section>

        <section className="lower-grid">
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
        </section>
      </section>
    </main>
  );
}

function StatusBadge({ status }: { status: RunSummary["status"] | ToolCallDetail["status"] }) {
  return <span className={`status-badge ${status}`}>{status.replace("_", " ")}</span>;
}

function RiskBadge({ risk }: { risk: ApprovalSummary["riskLevel"] }) {
  return <span className={`risk-badge ${risk}`}>{risk.replace("_", " ")}</span>;
}
