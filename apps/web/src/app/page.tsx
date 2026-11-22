"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import type { LiveApproval, LiveKnowledgeBase, LiveRetrievalResponse, LiveRun, LiveRunEvent } from "../lib/api";
import { errorMessage, isIdentity, useLiveApi, type Agent, type Document, type Identity } from "../lib/live-api";
import styles from "./workbench.module.css";

type Session = { token: string; identity: Identity };
type ApprovalTool = { id: string; run_id: string; approval_id: string; tool_name: string;
  arguments: Record<string, unknown>; risk_level: string; status: string };
const idPath = (id: string) => encodeURIComponent(id);
const isAbort = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

function IdDetails({ label, value }: { label: string; value: string }) {
  return <details className={styles.idDetails}>
    <summary>{label}</summary>
    <p className={styles.identifier}>{value}</p>
  </details>;
}

function Section({
  step, title, lead, headingId, children, className = "",
}: {
  step: number; title: string; lead: string; headingId: string; children: ReactNode; className?: string;
}) {
  return <section className={`${styles.section} ${className}`.trim()} aria-labelledby={headingId}>
    <div className={styles.sectionTitle}>
      <span className={styles.flowIndex} aria-hidden="true">{step}</span>
      <h2 id={headingId}>{title}</h2>
    </div>
    <p className={styles.sectionLead}>{lead}</p>
    {children}
  </section>;
}

export default function Page() {
  const [generation, setGeneration] = useState(0);
  const [notice, setNotice] = useState("");
  const clearSession = useCallback((expired = false) => {
    setNotice(expired ? "Session expired. Sign in again." : "");
    setGeneration((value) => value + 1);
  }, []);
  return <SessionPage key={generation} notice={notice} clearSession={clearSession} />;
}

function SessionPage({ notice, clearSession }: { notice: string; clearSession: (expired?: boolean) => void }) {
  const [session, setSession] = useState<Session | null>(null);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(notice);
  const [health, setHealth] = useState("Checking API");
  const unauthorized = useCallback(() => clearSession(true), [clearSession]);
  const loginApi = useLiveApi(key.trim(), unauthorized);
  const anonymousApi = useLiveApi("", unauthorized);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/agent-kernel/health", { credentials: "omit", cache: "no-store", signal: controller.signal })
      .then((response) => response.json())
      .then((data) => { if (!controller.signal.aborted) setHealth(data.state === "online" ? "API reachable" : "API unreachable"); })
      .catch(() => { if (!controller.signal.aborted) setHealth("API unreachable"); });
    return () => controller.abort();
  }, []);

  async function signIn(anonymous = false) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const identity = await (anonymous ? anonymousApi : loginApi)<unknown>("auth/me");
      if (!isIdentity(identity) || (anonymous ? identity.authenticated : !identity.authenticated)) {
        setError(anonymous ? "Anonymous access is not available." : "Authentication is disabled. Use anonymous access explicitly.");
        return;
      }
      setSession({ token: anonymous ? "" : key.trim(), identity });
      setKey("");
    } catch (cause) {
      if (!isAbort(cause)) setError(errorMessage(cause));
    } finally { setBusy(false); }
  }

  return <main className={styles.workbench}>
    <header className={styles.header}>
      <div><p className={styles.eyebrow}>Agent Kernel</p><h1>Agent Workbench</h1></div>
      <div className={styles.headerActions}>
        <span aria-label="Runtime status" className={styles.health}>{health}</span>
        {session && <button type="button" onClick={() => clearSession()}>Sign out</button>}
      </div>
    </header>
    {!session ? <section className={styles.login} aria-labelledby="login-heading">
      <h2 id="login-heading">Workspace sign in</h2>
      <form onSubmit={(event) => { event.preventDefault(); void signIn(); }}>
        <label>API key<input type="password" value={key} onChange={(event) => setKey(event.target.value)}
          autoComplete="off" spellCheck={false} maxLength={4000} required disabled={busy} /></label>
        <div className={styles.actions}>
          <button type="submit" disabled={busy || !key.trim()}>Sign in</button>
          <button type="button" disabled={busy} onClick={() => void signIn(true)}>Continue anonymously</button>
        </div>
      </form>
      {error && <p role="alert" className={styles.error}>{error}</p>}
    </section> : <LiveWorkspace session={session} onUnauthorized={unauthorized} />}
  </main>;
}

function LiveWorkspace({ session, onUnauthorized }: { session: Session; onUnauthorized: () => void }) {
  const api = useLiveApi(session.token, onUnauthorized);
  const { identity } = session;
  const can = (permission: string) => !identity.authenticated || identity.permissions.includes(permission);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentsReady, setAgentsReady] = useState(false);
  const [agentId, setAgentId] = useState("");
  const [agentName, setAgentName] = useState("");
  const [knowledgeBases, setKnowledgeBases] = useState<LiveKnowledgeBase[]>([]);
  const [knowledgeReady, setKnowledgeReady] = useState(false);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [kbId, setKbId] = useState("");
  const [kbName, setKbName] = useState("");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileVersion, setFileVersion] = useState(0);
  const [documentResult, setDocumentResult] = useState<unknown>(null);
  const [query, setQuery] = useState("");
  const [retrieval, setRetrieval] = useState<LiveRetrievalResponse | null>(null);
  const [task, setTask] = useState("");
  const [model, setModel] = useState("mock:echo");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [runIdInput, setRunIdInput] = useState("");
  const [run, setRun] = useState<LiveRun | null>(null);
  const [events, setEvents] = useState<LiveRunEvent[]>([]);
  const [approvals, setApprovals] = useState<LiveApproval[]>([]);
  const [resumeApprovalId, setResumeApprovalId] = useState("");
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const resultsRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    let active = true;
    if (!identity.authenticated || identity.permissions.includes("agent:read")) {
      void api<Agent[]>("agents").then((data) => {
        if (active) { setAgents(data); setAgentId(data[0]?.id ?? ""); }
      }).catch((cause) => { if (active && !isAbort(cause)) setError(errorMessage(cause)); })
        .finally(() => { if (active) setAgentsReady(true); });
    }
    if (!identity.authenticated || identity.permissions.includes("knowledge:read")) {
      void api<LiveKnowledgeBase[]>("knowledge-bases").then((data) => {
        if (active) { setKnowledgeBases(data); setKbId(data[0]?.id ?? ""); }
      }).catch((cause) => { if (active && !isAbort(cause)) setError(errorMessage(cause)); })
        .finally(() => { if (active) setKnowledgeReady(true); });
    }
    return () => { active = false; };
  }, [api, identity]);

  useEffect(() => {
    let active = true;
    setDocuments([]); setDocumentId(""); setDocumentResult(null); setRetrieval(null);
    setFile(null); setFileVersion((value) => value + 1);
    if (kbId && (!identity.authenticated || identity.permissions.includes("knowledge:read"))) {
      setDocumentsLoading(true);
      void api<Document[]>(`knowledge-bases/${idPath(kbId)}/documents`).then((data) => {
        if (active) { setDocuments(data); setDocumentId(data[0]?.id ?? ""); }
      }).catch((cause) => { if (active && !isAbort(cause)) setError(errorMessage(cause)); })
        .finally(() => { if (active) setDocumentsLoading(false); });
    } else setDocumentsLoading(false);
    return () => { active = false; };
  }, [api, kbId, identity]);

  useEffect(() => {
    if (run) resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [run?.id]);

  async function action(operation: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true); setError(""); setNotice("");
    try { await operation(); }
    catch (cause) { if (!isAbort(cause)) setError(errorMessage(cause)); }
    finally { busyRef.current = false; setBusy(false); }
  }
  function submit(operation: () => Promise<void>) {
    return (event: FormEvent) => { event.preventDefault(); void action(operation); };
  }
  async function refreshApprovals() {
    if (can("approval:review")) setApprovals(await api<LiveApproval[]>("approvals"));
  }
  async function refreshRun(id: string) {
    const current = await api<LiveRun>(`runs/${idPath(id)}`);
    setRun(current); setRunIdInput(current.id);
    setEvents(await api<LiveRunEvent[]>(`runs/${idPath(id)}/events`));
    await refreshApprovals();
  }
  async function runAction(operation: "queue" | "cancel" | "resume") {
    if (!run) return;
    const payload = operation === "resume" && resumeApprovalId ? { approval_id: resumeApprovalId } : {};
    const updated = await api<LiveRun>(`runs/${idPath(run.id)}/${operation}`, payload);
    setRun(updated);
    await refreshRun(updated.id);
  }
  async function documentAction(operation: "ingest" | "chunk" | "index") {
    const result = await api<unknown>(`documents/${idPath(documentId)}/${operation}`, {});
    setDocumentResult(result);
    const updated = await api<Document>(`documents/${idPath(documentId)}`);
    setDocuments((items) => items.map((item) => item.id === updated.id ? updated : item));
    setNotice(`${operation === "ingest" ? "Ingestion" : operation === "chunk" ? "Chunking" : "Indexing"} request completed.`);
  }
  async function decide(approval: LiveApproval, decision: "approve" | "reject", note: string) {
    const updated = await api<LiveApproval>(`approvals/${idPath(approval.id)}/${decision}`,
      decision === "approve" ? { decision_note: note || null } : { reason: note.trim() });
    setApprovals((items) => items.map((item) => item.id === updated.id ? updated : item));
    setResumeApprovalId(updated.id);
    if (run) await refreshRun(run.id);
  }
  const document = documents.find((item) => item.id === documentId);
  const runApprovals = approvals.filter((approval) => approval.run_id === run?.id);
  const resolvedApprovals = runApprovals.filter((approval) => ["approved", "rejected"].includes(approval.status));
  const pendingApprovals = runApprovals.filter((approval) => approval.status === "requested");

  return <>
    <section className={styles.identity} aria-label="Identity">
      <strong>{identity.authenticated ? identity.display_name ?? identity.principal_id : "Anonymous (authentication disabled)"}</strong>
      <span>{identity.role ?? "Unrestricted"}</span><span>Workspace: {identity.workspace_id ?? "Unscoped"}</span>
    </section>
    <nav className={styles.flow} aria-label="Workbench flow">
      {([
        { index: "1", label: "Agents", active: !run },
        { index: "2", label: "Knowledge", active: !run },
        { index: "3", label: "Runs", active: !run },
        { index: "4", label: "Results", active: Boolean(run) },
      ] as const).map((step) => (
        <span key={step.label} className={styles.flowStep}>
          <span className={`${styles.flowIndex} ${step.active ? styles.flowIndexActive : ""}`.trim()} aria-hidden="true">{step.index}</span>
          <strong>{step.label}</strong>
        </span>
      ))}
    </nav>
    <div className={styles.feedback} aria-live="polite">
      {error ? <p role="alert" className={styles.error}>{error}</p> : <p>{busy ? "Working..." : notice || "Connected"}</p>}
    </div>

    <div className={styles.setup}>
      <Section step={1} title="Agents" headingId="agents-heading" lead="Select or create the agent that owns the next run.">
        <form onSubmit={submit(async () => {
          const created = await api<Agent>("agents", { name: agentName.trim() });
          setAgents((items) => [...items, created]); setAgentId(created.id); setAgentName("");
        })}>
          <label>Agent name<input value={agentName} onChange={(event) => setAgentName(event.target.value)} maxLength={255} required /></label>
          <button disabled={busy || !agentsReady || !can("agent:write") || !agentName.trim()}>Create agent</button>
        </form>
        <label>Agent<select value={agentId} disabled={busy} onChange={(event) => setAgentId(event.target.value)}>
          <option value="">Select agent</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
        </select></label>
        {agentId && <IdDetails label="Show agent ID" value={agentId} />}
      </Section>

      <Section step={2} title="Knowledge" headingId="knowledge-heading" lead="Prepare a knowledge base, then ingest → chunk → index before retrieval.">
        <form onSubmit={submit(async () => {
          const created = await api<LiveKnowledgeBase>("knowledge-bases", { name: kbName.trim() });
          setKnowledgeBases((items) => [...items, created]); setDocumentsLoading(true); setKbId(created.id); setKbName("");
        })}>
          <label>Knowledge base name<input value={kbName} onChange={(event) => setKbName(event.target.value)} maxLength={255} required /></label>
          <button disabled={busy || !knowledgeReady || !can("knowledge:write") || !kbName.trim()}>Create knowledge base</button>
        </form>
        <label>Knowledge base<select value={kbId} disabled={busy} onChange={(event) => { setDocumentsLoading(true); setKbId(event.target.value); }}>
          <option value="">Select knowledge base</option>{knowledgeBases.map((kb) => <option key={kb.id} value={kb.id}>{kb.name}</option>)}
        </select></label>
        {kbId && <IdDetails label="Show knowledge base ID" value={kbId} />}
        <form onSubmit={submit(async () => {
          if (!file) return;
          const body = new FormData(); body.set("file", file);
          const uploaded = await api<Document>(`knowledge-bases/${idPath(kbId)}/documents/upload`, body);
          setDocuments((items) => [...items, uploaded]); setDocumentId(uploaded.id);
          setFile(null); setFileVersion((value) => value + 1); setDocumentResult(null);
        })}>
          <label>Document file<input key={fileVersion} type="file" disabled={busy || documentsLoading || !kbId || !can("knowledge:write")}
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              if (selected && selected.size > 8 * 1024 * 1024) {
                event.target.value = ""; setFile(null); setError("Document exceeds the 8 MiB upload limit.");
              } else { setFile(selected); setError(""); }
            }} /></label>
          <button disabled={busy || documentsLoading || !file || !kbId || !can("knowledge:write")}>Upload document</button>
        </form>
        <label>Document<select value={documentId} disabled={busy} onChange={(event) => { setDocumentId(event.target.value); setDocumentResult(null); }}>
          <option value="">Select document</option>{documents.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select></label>
        {document && <IdDetails label={`Show document ID (${document.status})`} value={document.id} />}
        <div className={styles.actions}>
          <button disabled={busy || !documentId || !can("knowledge:write")} onClick={() => void action(() => documentAction("ingest"))}>Ingest document</button>
          <button disabled={busy || !documentId || !can("knowledge:write")} onClick={() => void action(() => documentAction("chunk"))}>Chunk document</button>
          <button disabled={busy || !documentId || !can("knowledge:write")} onClick={() => void action(() => documentAction("index"))}>Index document</button>
          <button disabled={busy || !documentId || !can("knowledge:read")} onClick={() => void action(async () => {
            setDocumentResult(await api<unknown>(`documents/${idPath(documentId)}/chunks`));
          })}>Inspect chunks</button>
        </div>
        {documentResult !== null && <details><summary>Document result</summary><pre>{JSON.stringify(documentResult, null, 2)}</pre></details>}
        <form onSubmit={submit(async () => {
          setRetrieval(null);
          setRetrieval(await api<LiveRetrievalResponse>(`knowledge-bases/${idPath(kbId)}/retrieve`, { query: query.trim(), top_k: 5 }));
        })}>
          <label>Search query<input value={query} onChange={(event) => setQuery(event.target.value)} maxLength={4000} required /></label>
          <button disabled={busy || !kbId || !query.trim() || !can("knowledge:read")}>Retrieve</button>
        </form>
        {retrieval && <div aria-label="Retrieval results" data-testid="retrieval-results">
          {retrieval.results.length === 0 && <p>No matching chunks.</p>}
          {retrieval.results.map((result) => <article className={styles.result} key={result.citation.chunk_id}>
            <h3>{result.citation.document_title}</h3><p>{result.content}</p>
            <details className={styles.idDetails}>
              <summary>Show citation IDs</summary>
              <p className={styles.identifier}>Document: {result.citation.document_id}</p>
              <p className={styles.identifier}>Chunk: {result.citation.chunk_id}</p>
              <p className={styles.identifier}>{result.citation.document_source_uri}</p>
            </details>
            <span>Score: {result.score.toFixed(4)}</span>
          </article>)}
        </div>}
      </Section>

      <Section step={3} title="Runs" headingId="runs-heading" className={styles.runSection}
        lead="Create a run for the selected agent, then queue it. Results open below.">
        <form onSubmit={submit(async () => {
          const input: Record<string, unknown> = { task };
          input.model = model.trim() || "mock:echo";
          if (systemPrompt.trim()) input.messages = [
            { role: "system", content: systemPrompt }, { role: "user", content: task },
          ];
          const created = await api<LiveRun>(`agents/${idPath(agentId)}/runs`, { input });
          setRun(created); setRunIdInput(created.id); setEvents([]); setApprovals([]); setResumeApprovalId("");
        })}>
          <label>Model<input value={model} onChange={(event) => setModel(event.target.value)} maxLength={255} /></label>
          <details className={styles.advanced}>
            <summary>Advanced options</summary>
            <label>System prompt<textarea aria-label="System prompt" value={systemPrompt} onChange={(event) => setSystemPrompt(event.target.value)} rows={3} maxLength={64000} /></label>
          </details>
          <label>Task<textarea aria-label="Task" value={task} onChange={(event) => setTask(event.target.value)} required rows={5} maxLength={64000} /></label>
          <button disabled={busy || !agentId || !task.trim() || !can("run:write")}>Create run</button>
        </form>
        <form onSubmit={submit(async () => {
          setRun(null); setEvents([]); setApprovals([]); setResumeApprovalId("");
          await refreshRun(runIdInput.trim());
        })}>
          <label>Run ID<input value={runIdInput} onChange={(event) => setRunIdInput(event.target.value)} required /></label>
          <button disabled={busy || !runIdInput.trim() || !can("run:read")}>Lookup run</button>
        </form>
      </Section>
    </div>

    {run && <section ref={resultsRef} className={styles.results} aria-labelledby="results-heading">
      <div className={styles.resultsHeader}>
        <div>
          <div className={styles.sectionTitle}>
            <span className={`${styles.flowIndex} ${styles.flowIndexActive}`} aria-hidden="true">4</span>
            <h2 id="results-heading">Results</h2>
          </div>
          <IdDetails label="Show run ID" value={run.id} />
        </div>
        <span className={styles.statusBadge} data-status={run.status} data-testid="run-status">{run.status}</span>
      </div>

      <div className={styles.actions}>
        <button disabled={busy || run.status !== "created" || !can("run:write")} onClick={() => void action(() => runAction("queue"))}>Queue run</button>
        <button disabled={busy || !can("run:read")} onClick={() => void action(() => refreshRun(run.id))}>Refresh run</button>
        <button disabled={busy || ["succeeded", "failed", "canceled"].includes(run.status) || !can("run:write")} onClick={() => void action(() => runAction("cancel"))}>Cancel run</button>
      </div>
      {run.error_type && <p role="alert" className={styles.error}>{run.error_type}: {run.error_message}</p>}

      <div className={styles.resultsGrid}>
        <div className={styles.resultsPrimary}>
          <section className={styles.approvals} aria-labelledby="approvals-heading">
            <h3 id="approvals-heading">Approvals {pendingApprovals.length ? `(${pendingApprovals.length} pending)` : ""}</h3>
            {!can("approval:review") ? <p>Approval review permission required.</p> : runApprovals.length === 0 ? <p>No approvals for this run.</p> :
              runApprovals.map((approval) => <ApprovalCard key={approval.id} approval={approval} busy={busy} api={api}
                decide={(decision, note) => void action(() => decide(approval, decision, note))} />)}
          </section>
          <label>Resume approval<select value={resumeApprovalId} disabled={busy} onChange={(event) => setResumeApprovalId(event.target.value)}>
            <option value="">Latest decision</option>{resolvedApprovals.map((approval) => <option key={approval.id} value={approval.id}>{approval.id} ({approval.status})</option>)}
          </select></label>
          <button disabled={busy || run.status !== "waiting_approval" || !resolvedApprovals.length || !can("run:write")} onClick={() => void action(() => runAction("resume"))}>Resume run</button>
        </div>
        <div className={styles.resultsSecondary}>
          <h3>Events</h3>
          <ol className={styles.events} aria-label="Run events">{events.map((event) => <li key={event.id}>
            <details><summary>{event.sequence}. {event.type}</summary><pre>{JSON.stringify(event.payload, null, 2)}</pre></details>
          </li>)}</ol>
          <h3>Output and citations</h3>
          <pre data-testid="run-output">{run.output ? JSON.stringify(run.output, null, 2) : "No output yet."}</pre>
        </div>
      </div>
    </section>}
  </>;
}

function ApprovalCard({ approval, busy, decide, api }: {
  approval: LiveApproval; busy: boolean; decide: (decision: "approve" | "reject", note: string) => void;
  api: ReturnType<typeof useLiveApi>;
}) {
  const [note, setNote] = useState("");
  const [tool, setTool] = useState<ApprovalTool | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setTool(null); setError("");
    void api<ApprovalTool>(`approvals/${idPath(approval.id)}/tool-call`).then((data) => {
      if (!active) return;
      if (data.id !== approval.tool_call_id || data.run_id !== approval.run_id || data.approval_id !== approval.id) {
        setError("Approval tool binding is inconsistent."); return;
      }
      setTool(data);
    }).catch((cause) => { if (active && !isAbort(cause)) setError(errorMessage(cause)); });
    return () => { active = false; };
  }, [api, approval.id, approval.run_id, approval.tool_call_id, approval.status]);
  return <article className={styles.approval} data-testid={`approval-${approval.id}`} aria-label={`Approval ${approval.id}`}>
    <IdDetails label="Show approval ID" value={approval.id} />
    <strong>{approval.status}</strong>
    <p>{approval.reason}</p>
    <IdDetails label="Show tool call ID" value={approval.tool_call_id} />
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {tool ? <><h4>{tool.tool_name}</h4><p>Risk: {tool.risk_level}</p>
      <pre aria-label="Tool arguments">{JSON.stringify(tool.arguments, null, 2)}</pre></> : !error && <p>Loading tool details...</p>}
    {approval.decision_note && <p>{approval.decision_note}</p>}
    <label>Decision note<textarea aria-label="Decision note" value={note} onChange={(event) => setNote(event.target.value)} maxLength={4000} rows={2}
      disabled={busy || approval.status !== "requested"} /></label>
    <div className={styles.actions}>
      <button disabled={busy || !tool || approval.status !== "requested"} onClick={() => decide("approve", note)}>Approve</button>
      <button disabled={busy || !tool || approval.status !== "requested" || !note.trim()} onClick={() => decide("reject", note)}>Reject</button>
    </div>
  </article>;
}
