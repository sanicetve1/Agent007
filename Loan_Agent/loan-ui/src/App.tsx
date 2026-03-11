import React, { useEffect, useMemo, useState } from "react";
import "./App.css";

type Applicant = {
  applicant_id: string;
  full_name: string;
  annual_income: number;
  kyc_status: string;
};

type LoanChoice = {
  loan_id: string;
  loan_type: string;
  outstanding_amount: number;
  status: string;
  start_date: string;
};

type ToolCallTrace = {
  step: number;
  tool: string;
  args: Record<string, any>;
  status: string;
  attempts: number;
  error?: string | null;
  result: Record<string, any>;
};

type LlmOutcomeAnalysis = {
  approval_summary?: string;
  decision?: string;
  overall_risk_level?: string;
  key_strengths?: string[];
  key_risks?: string[];
  next_actions?: string[];
  customer_information_used?: string[];
  analysis_findings?: string[];
  final_verdict?: string;
};

type AgentTraceStep = {
  step_index: number;
  step_type: string;
  detail: Record<string, any>;
};

type ClarificationOption = { applicant_id: string; full_name: string };
type ChatMessage = { from: "user" | "agent"; text: string };

type AgentResult = {
  applicant_id?: string;
  overall_risk_level?: string;
  recommendation?: string;
  explanation?: string;
  tool_failed?: boolean;
  missing_data?: string[];
  tool_call_sequence?: ToolCallTrace[];
  llm_outcome_analysis?: LlmOutcomeAnalysis;
  agent_mode?: string;
  agent_trace?: AgentTraceStep[];
  clarification_question?: string;
  clarification_options?: ClarificationOption[];
  [k: string]: any;
};

// VITE_API_BASE set at build time: /api for production (nginx proxy), http://localhost:8001 for dev
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8001";

const TOOL_ICONS: Record<string, string> = {
  calculate_credit_risk: "💳",
  analyze_cashflow: "📊",
  list_applicant_loans: "🏦",
  assess_collateral: "🏠",
};

function App() {
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [selectedApplicant, setSelectedApplicant] = useState("");
  const [months, setMonths] = useState(6);
  const [thresholdRatio, setThresholdRatio] = useState(1.0);
  const [loans, setLoans] = useState<LoanChoice[]>([]);
  const [selectedLoan, setSelectedLoan] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "sequence" | "json">("overview");
  const [clarificationReply, setClarificationReply] = useState("");
  const [toast, setToast] = useState<{ id: number; type: "error" | "info"; message: string } | null>(null);
  const [agentRunning, setAgentRunning] = useState(false);
  const [chatByCustomer, setChatByCustomer] = useState<Record<string, { sessionId?: string; messages: ChatMessage[] }>>({});
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const toastIdRef = React.useRef(0);
  const selectedApplicantRef = React.useRef(selectedApplicant);
  const chatEndRef = React.useRef<HTMLDivElement | null>(null);
  selectedApplicantRef.current = selectedApplicant;

  useEffect(() => {
    async function loadApplicants() {
      try {
        const resp = await fetch(`${API_BASE}/data/applicants`);
        if (!resp.ok) throw new Error(`Failed to load applicants (${resp.status})`);
        const data: Applicant[] = await resp.json();
        setApplicants(data);
        if (data.length > 0) setSelectedApplicant((prev) => prev || data[0].applicant_id);
      } catch (err: any) {
        setError(err.message ?? "Failed to load applicants");
      }
    }
    loadApplicants();
  }, []);

  /** Fetch loans for the selected customer only (for dropdown); does not set agent result. */
  async function fetchLoansForCustomer(applicantId: string) {
    try {
      const data = await callApi("/tools/list_applicant_loans", { applicant_id: applicantId });
      if (selectedApplicantRef.current !== applicantId) return;
      const choices = data.loan_choices || [];
      setLoans(choices);
      setSelectedLoan(choices.length ? choices[0].loan_id : "");
    } catch {
      if (selectedApplicantRef.current !== applicantId) return;
      setLoans([]);
      setSelectedLoan("");
    }
  }

  useEffect(() => {
    // When switching customer, reset per-run UI state so context is clear.
    setResult(null);
    setClarificationReply("");
    setError(null);
    setAgentRunning(false);
    setActiveTab("overview");
    setChatInput("");

    if (!selectedApplicant) {
      setLoans([]);
      setSelectedLoan("");
      return;
    }
    fetchLoansForCustomer(selectedApplicant);
  }, [selectedApplicant]);

  const selectedApplicantObject = useMemo(
    () => applicants.find((x) => x.applicant_id === selectedApplicant) || null,
    [applicants, selectedApplicant]
  );
  const activeChat = selectedApplicant ? chatByCustomer[selectedApplicant] || { sessionId: undefined, messages: [] } : { sessionId: undefined, messages: [] };

  function showToast(type: "error" | "info", message: string) {
    toastIdRef.current += 1;
    setToast({ id: toastIdRef.current, type, message });
    setTimeout(() => setToast((t) => (t?.id === toastIdRef.current ? null : t)), 5000);
  }

  async function callApi(path: string, payload: Record<string, any>) {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const body = await resp.text();
      throw new Error(body || `Request failed (${resp.status})`);
    }
    return resp.json();
  }

  function clearSession() {
    setResult(null);
    setClarificationReply("");
    setError(null);
    setAgentRunning(false);
    if (selectedApplicant) {
      setChatByCustomer((prev) => {
        const existing = prev[selectedApplicant] || { sessionId: prev[selectedApplicant]?.sessionId, messages: [] };
        return {
          ...prev,
          [selectedApplicant]: { ...existing, messages: [] },
        };
      });
    }
  }

  async function runCreditRisk() {
    setLoading(true);
    setError(null);
    try {
      const data = await callApi("/tools/calculate_credit_risk", { applicant_id: selectedApplicant });
      setResult(data);
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }

  async function runCashflow() {
    setLoading(true);
    setError(null);
    try {
      const data = await callApi("/tools/analyze_cashflow", { applicant_id: selectedApplicant, months });
      setResult(data);
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }

  async function runListLoans() {
    setLoading(true);
    setError(null);
    try {
      const data = await callApi("/tools/list_applicant_loans", { applicant_id: selectedApplicant });
      setLoans(data.loan_choices || []);
      if (data.loan_choices?.length) {
        setSelectedLoan(data.loan_choices[0].loan_id);
      } else {
        setSelectedLoan("");
      }
      setResult(data);
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }

  async function runCollateral() {
    if (!selectedLoan) {
      setError("Select a loan first.");
      showToast("error", "Select a loan first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await callApi("/tools/assess_collateral", {
        loan_id: selectedLoan,
        threshold_ratio: thresholdRatio,
      });
      setResult(data);
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }

  async function runUseCasePreScreen() {
    setLoading(true);
    setError(null);
    setAgentRunning(true);
    try {
      const data = await callApi("/agent/run", {
        applicant_id: selectedApplicant,
        months,
      });
      if (data.loan_options?.length) {
        setLoans(data.loan_options);
        setSelectedLoan(data.loan_options[0].loan_id);
      }
      setResult(data);
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
      setAgentRunning(false);
    }
  }

  async function runUseCaseFull() {
    setLoading(true);
    setError(null);
    setAgentRunning(true);
    try {
      const data = await callApi("/agent/run", {
        applicant_id: selectedApplicant,
        loan_id: selectedLoan || undefined,
        months,
      });
      setResult(data);
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
      setAgentRunning(false);
    }
  }

  /** Start agent without applicant to trigger clarification (autonomy mode only). */
  async function runTestClarification() {
    setLoading(true);
    setError(null);
    setResult(null);
    setClarificationReply("");
    setAgentRunning(true);
    try {
      const data = await callApi("/agent/run", {
        applicant_id: null,
        months,
      });
      setResult(data);
      if (data?.status === "clarification_needed") showToast("info", "Agent needs more information.");
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
      setAgentRunning(false);
    }
  }

  /** Send reply after clarification_needed (customer name or applicant_id). */
  async function sendClarificationReply(replyOverride?: string) {
    const sessionId = result?.session_id;
    const reply = (replyOverride ?? clarificationReply).trim();
    if (!sessionId || !reply) return;
    setLoading(true);
    setError(null);
    setAgentRunning(true);
    try {
      const data = await callApi("/agent/continue", {
        session_id: sessionId,
        user_reply: reply,
      });
      setResult(data);
      if (!replyOverride) setClarificationReply("");
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
      setAgentRunning(false);
    }
  }

  async function runAllTools() {
    setLoading(true);
    setError(null);
    try {
      const credit = await callApi("/tools/calculate_credit_risk", { applicant_id: selectedApplicant });
      const cashflow = await callApi("/tools/analyze_cashflow", { applicant_id: selectedApplicant, months });
      const loanList = await callApi("/tools/list_applicant_loans", { applicant_id: selectedApplicant });
      const firstLoanId = loanList.loan_choices?.[0]?.loan_id || "";
      if (firstLoanId) {
        setSelectedLoan(firstLoanId);
      }
      const collateral = firstLoanId
        ? await callApi("/tools/assess_collateral", { loan_id: firstLoanId, threshold_ratio: thresholdRatio })
        : { warning: "No active loan found for collateral check." };
      setResult({ credit_risk: credit, cashflow_signal: cashflow, loans: loanList, collateral_status: collateral });
    } catch (err: any) {
      const msg = err.message ?? "Request failed";
      setError(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }

  async function sendChatMessage() {
    if (!selectedApplicant || !chatInput.trim() || chatLoading) return;
    const customerId = selectedApplicant;
    const message = chatInput.trim();
    const existing = chatByCustomer[customerId] || { sessionId: undefined, messages: [] };

    // Optimistically append user message
    setChatByCustomer((prev) => ({
      ...prev,
      [customerId]: {
        sessionId: existing.sessionId,
        messages: [...(prev[customerId]?.messages || []), { from: "user", text: message }],
      },
    }));
    setChatInput("");
    setChatLoading(true);

    try {
      const data = await callApi("/agent/chat", {
        applicant_id: customerId,
        message,
        session_id: existing.sessionId || null,
      });
      if (data.status && data.status !== "ok") {
        const errMsg = data.error || "Chat request failed";
        showToast("error", errMsg);
        setChatLoading(false);
        return;
      }
      const answer: string = data.answer || "I could not generate an answer for this question.";
      const sessionId: string | undefined = data.session_id;
      setChatByCustomer((prev) => {
        const base = prev[customerId] || { sessionId, messages: [] };
        return {
          ...prev,
          [customerId]: {
            sessionId: sessionId || base.sessionId,
            messages: [...base.messages, { from: "agent", text: answer }],
          },
        };
      });
    } catch (err: any) {
      const msg = err.message ?? "Chat request failed";
      showToast("error", msg);
    } finally {
      setChatLoading(false);
    }
  }

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [selectedApplicant, activeChat.messages.length]);

  const stepsTotal = result?.tool_call_sequence?.length ?? result?.agent_trace?.length ?? 0;

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-left">
          <h1>Loan Agent</h1>
          {result?.session_id && (
            <span className="session-pill">
              Session: <span>{String(result.session_id).slice(0, 8)}…</span>
            </span>
          )}
        </div>
      </header>

      <main className="app-main">
        <section className="panel controls">
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>Customers</h2>
          <div className="selector-grid customer-list">
            {applicants.map((a) => (
              <div
                key={a.applicant_id}
                className={`card selector-card ${selectedApplicant === a.applicant_id ? "selected" : ""}`}
                onClick={() => !loading && setSelectedApplicant(a.applicant_id)}
              >
                <div className="card-name">{a.full_name}</div>
                <div className="card-summary">
                  Income: {a.annual_income.toLocaleString()} · KYC: {a.kyc_status}
                </div>
              </div>
            ))}
          </div>
          <details className="action-group testing" style={{ marginTop: "1rem" }}>
            <summary>Debug &amp; testing</summary>
            <div className="testing-inner">
              <button className="btn-secondary" onClick={runTestClarification} disabled={loading}>
                Test clarification (no customer)
              </button>
              <div className="button-row">
                <button onClick={runCreditRisk} disabled={loading || !selectedApplicant}>💳 Credit risk</button>
                <button onClick={runCashflow} disabled={loading || !selectedApplicant}>📊 Cashflow</button>
                <button onClick={() => selectedApplicant && fetchLoansForCustomer(selectedApplicant)} disabled={loading || !selectedApplicant}>🏦 Refresh loans</button>
                <button onClick={runCollateral} disabled={loading || !selectedLoan}>🏠 Collateral</button>
              </div>
            </div>
          </details>
          {error && <div className="error" style={{ marginTop: "0.75rem" }}>{error}</div>}
        </section>

        <section className="panel results">
          {selectedApplicantObject ? (
            <>
              <div className="customer-context">
                <h2 style={{ margin: "0 0 0.75rem", fontSize: "1.05rem" }}>Customer context</h2>
                <div className="demographics-card">
                  <div className="demographics-row">
                    <span className="demographics-k">Name</span>
                    <span className="demographics-v">{selectedApplicantObject.full_name}</span>
                  </div>
                  <div className="demographics-row">
                    <span className="demographics-k">Annual income</span>
                    <span className="demographics-v">{selectedApplicantObject.annual_income.toLocaleString()}</span>
                  </div>
                  <div className="demographics-row">
                    <span className="demographics-k">KYC status</span>
                    <span className={`badge ${selectedApplicantObject.kyc_status === "verified" ? "info" : "warning"}`}>{selectedApplicantObject.kyc_status}</span>
                  </div>
                  <div className="demographics-row">
                    <span className="demographics-k">Applicant ID</span>
                    <span className="demographics-v mono">{selectedApplicantObject.applicant_id.slice(0, 8)}…</span>
                  </div>
                </div>
                <div className="context-form">
                  <label className="label">
                    Loan
                    <select value={selectedLoan} onChange={(e) => setSelectedLoan(e.target.value)} disabled={loading}>
                      <option value="">No loans</option>
                      {loans.map((l) => (
                        <option key={l.loan_id} value={l.loan_id}>
                          {l.loan_type} · {l.outstanding_amount.toLocaleString()} ({l.status})
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="label">
                    Months
                    <input
                      type="number"
                      min={1}
                      max={24}
                      value={months}
                      onChange={(e) => setMonths(Number(e.target.value))}
                      disabled={loading}
                    />
                  </label>
                  <label className="label">
                    Threshold ratio
                    <input
                      type="number"
                      min={0.1}
                      step={0.1}
                      value={thresholdRatio}
                      onChange={(e) => setThresholdRatio(Number(e.target.value))}
                      disabled={loading}
                    />
                  </label>
                </div>
                <div className="context-actions">
                  <button className="btn-accent" onClick={runUseCaseFull} disabled={loading}>
                    Analyze applicant
                  </button>
                </div>

              <div className="chat-card">
                <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.95rem" }}>Chat about this customer</h3>
                <div className="chat-thread">
                  {activeChat.messages.length === 0 ? (
                    <p className="hint">Ask a question about this customer (e.g. last cash inflow, current loans).</p>
                  ) : (
                    activeChat.messages.map((m, idx) => (
                      <div key={idx} className={`chat-message ${m.from === "user" ? "user" : "agent"}`}>
                        <div className="chat-bubble">{m.text}</div>
                      </div>
                    ))
                  )}
                  <div ref={chatEndRef} />
                </div>
                <div className="chat-input-row">
                  <input
                    type="text"
                    placeholder="Ask a question about this customer"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendChatMessage()}
                    disabled={chatLoading || !selectedApplicant}
                  />
                  <button onClick={sendChatMessage} disabled={chatLoading || !selectedApplicant || !chatInput.trim()}>
                    {chatLoading ? "Sending..." : "Send"}
                  </button>
                </div>
                {chatLoading && <div className="chat-typing">Agent is thinking…</div>}
              </div>
              </div>

              {result?.status === "clarification_needed" && (
                <div className="clarification-block" style={{ marginTop: "1rem" }}>
                  <p>Agent asks for more information</p>
                  <p style={{ margin: 0, fontSize: "0.9rem" }}>{result.clarification_question}</p>
                  {result.clarification_options && result.clarification_options.length > 0 && (
                    <div className="clarification-options">
                      {result.clarification_options.map((opt) => (
                        <button key={opt.applicant_id} type="button" onClick={() => sendClarificationReply(opt.applicant_id)} disabled={loading}>
                          {opt.full_name}
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="clarification-input-row">
                    <input
                      type="text"
                      placeholder="Customer name or applicant_id (UUID)"
                      value={clarificationReply}
                      onChange={(e) => setClarificationReply(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && sendClarificationReply()}
                    />
                    <button onClick={() => sendClarificationReply()} disabled={loading || !clarificationReply.trim()}>Send reply</button>
                  </div>
                </div>
              )}

              <div className="results-header" style={{ marginTop: "1.25rem" }}>
                <h2>Agent output</h2>
                <div className="tab-row">
                  <button className={activeTab === "overview" ? "tab active" : "tab"} onClick={() => setActiveTab("overview")}>Overview</button>
                  <button className={activeTab === "sequence" ? "tab active" : "tab"} onClick={() => setActiveTab("sequence")}>Agent Sequence</button>
                  <button className={activeTab === "json" ? "tab active" : "tab"} onClick={() => setActiveTab("json")}>Raw JSON</button>
                </div>
              </div>

              {loading && agentRunning && (
                <div className="agent-running">
                  <div className="spinner-crystal" />
                  <p>Agent running…</p>
                  <span className="progress-steps">Working on tools</span>
                </div>
              )}

              {!loading && result && result.status !== "clarification_needed" && result.status !== "error" && activeTab === "overview" && (
                <div className="completion-badge">
                  <span className="check">✓</span> Complete
                  {stepsTotal > 0 && ` · ${stepsTotal} step${stepsTotal !== 1 ? "s" : ""}`}
                </div>
              )}

              {!result && !loading && <p className="hint">Select loan, months, and threshold above, then click &quot;Analyze applicant&quot;.</p>}
              {result?.status === "error" && (
                <div className="error">{result.message || result.error || "An error occurred."}</div>
              )}
              {result && result.status !== "clarification_needed" && result.status !== "error" && activeTab === "overview" && <OverviewTab result={result} />}
              {result && result.status !== "clarification_needed" && result.status !== "error" && activeTab === "sequence" && <SequenceTab result={result} />}
              {result && activeTab === "json" && <pre>{JSON.stringify(result, null, 2)}</pre>}
            </>
          ) : (
            <div className="customer-context-empty">
              <p className="hint">Select a customer from the list to see their details and run the agent.</p>
            </div>
          )}
        </section>
      </main>

      <footer className="app-footer">
        <div className="footer-actions">
          <button className="btn-accent" onClick={runUseCaseFull} disabled={loading || !selectedApplicant}>
            Run Agent
          </button>
          <button className="btn-secondary" onClick={clearSession}>
            Clear session
          </button>
        </div>
      </footer>

      {toast && (
        <div className="toast-container">
          <div className={`toast ${toast.type}`}>{toast.message}</div>
        </div>
      )}
    </div>
  );
}

function riskBadgeClass(level: string): "info" | "warning" | "risk" {
  const l = (level || "").toLowerCase();
  if (l.includes("high") || l.includes("decline") || l.includes("risk")) return "risk";
  if (l.includes("medium") || l.includes("conditional") || l.includes("caution")) return "warning";
  return "info";
}

function OverviewTab({ result }: { result: AgentResult }) {
  const analysis = result.llm_outcome_analysis || {};
  const strengths = analysis.key_strengths || [];
  const risks = analysis.key_risks || [];
  const actions = analysis.next_actions || [];

  const customerInfoUsed = analysis.customer_information_used || [];
  const analysisFindings = analysis.analysis_findings || [];
  const finalVerdict = analysis.final_verdict || "";
  const hasStructuredSuggestion = customerInfoUsed.length > 0 || analysisFindings.length > 0 || finalVerdict;

  const decision = analysis.decision || result.recommendation || "N/A";
  const riskLevel = analysis.overall_risk_level || result.overall_risk_level || "N/A";

  const baseExplanation = analysis.approval_summary || result.explanation || finalVerdict;
  const effectiveCustomerInfoUsed =
    customerInfoUsed.length > 0
      ? customerInfoUsed
      : baseExplanation
      ? [
          "Customer loan data (outstanding amounts, loan type, status).",
          "Customer risk profile (credit score, DTI, risk level from tools).",
          "Income and cashflow (income, expenses, volatility, net cashflow).",
          "Other underwriting rules and signals (e.g. collateral coverage, cashflow stability).",
        ]
      : [];
  const effectiveAnalysisFindings =
    analysisFindings.length > 0
      ? analysisFindings
      : baseExplanation
      ? [baseExplanation]
      : [];

  return (
    <div className="overview">
      {result.agent_mode && (
        <p className="hint" style={{ marginBottom: "0.5rem" }}>
          Agent mode: <strong>{result.agent_mode === "autonomous" ? "Autonomous (ReAct)" : "Deterministic"}</strong>
        </p>
      )}
      <div className="summary-grid">
        <div className="summary-card">
          <div className="k">Decision</div>
          <div className="v">
            <span className={`badge ${riskBadgeClass(decision)}`}>{decision}</span>
          </div>
        </div>
        <div className="summary-card">
          <div className="k">Overall Risk</div>
          <div className="v">
            <span className={`badge ${riskBadgeClass(riskLevel)}`}>{riskLevel}</span>
          </div>
        </div>
        <div className="summary-card">
          <div className="k">Tool Failures</div>
          <div className="v">{result.tool_failed ? <span className="badge risk">Yes</span> : <span className="badge info">No</span>}</div>
        </div>
      </div>

      <details open className="collapse">
        <summary>LLM Suggestion</summary>
        {hasStructuredSuggestion ? (
          <div className="llm-suggestion">
            <>
              <p className="llm-section-title">1. Customer information used to analyze</p>
              {effectiveCustomerInfoUsed.length > 0 ? (
                <ul>{effectiveCustomerInfoUsed.map((s, i) => <li key={i}>{s}</li>)}</ul>
              ) : (
                <p className="muted">No structured customer information details available.</p>
              )}
            </>
            <>
              <p className="llm-section-title">2. Based on this analysis we see</p>
              {effectiveAnalysisFindings.length > 0 ? (
                <ul>{effectiveAnalysisFindings.map((s, i) => <li key={i}>{s}</li>)}</ul>
              ) : (
                <p className="muted">No structured findings available.</p>
              )}
            </>
            {finalVerdict && (
              <>
                <p className="llm-section-title">3. Final verdict</p>
                <p>{finalVerdict}</p>
              </>
            )}
          </div>
        ) : (
          <p>{analysis.approval_summary || result.explanation || "No summary available."}</p>
        )}
      </details>

      <details className="collapse">
        <summary>Key Strengths</summary>
        {strengths.length === 0 ? <p className="muted">No strengths listed.</p> : <ul>{strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>}
      </details>

      <details className="collapse">
        <summary>Key Risks</summary>
        {risks.length === 0 ? <p className="muted">No risks listed.</p> : <ul>{risks.map((s, i) => <li key={i}>{s}</li>)}</ul>}
      </details>

      <details className="collapse">
        <summary>Next Actions</summary>
        {actions.length === 0 ? <p className="muted">No next actions listed.</p> : <ul>{actions.map((s, i) => <li key={i}>{s}</li>)}</ul>}
      </details>
    </div>
  );
}

function SequenceTab({ result }: { result: AgentResult }) {
  const isAutonomous = result.agent_mode === "autonomous";
  const agentTrace = result.agent_trace || [];
  const toolSequence = result.tool_call_sequence || [];
  let toolIndex = 0;

  if (isAutonomous && agentTrace.length > 0) {
    const stepLabel = (t: AgentTraceStep) => {
      switch (t.step_type) {
        case "intent":
          return "Intent detected";
        case "plan":
          return "Plan created";
        case "observation":
          return `Tool ${(t.detail?.tool as string) || "?"} executed`;
        case "reasoning":
          return "Reasoning";
        case "decision":
          return "Decision generated";
        default:
          return t.step_type;
      }
    };
    const getObservationToolIndex = (traceIndex: number) => {
      let n = 0;
      for (let i = 0; i < traceIndex; i++) if (agentTrace[i].step_type === "observation") n++;
      return n;
    };
    return (
      <div className="sequence">
        <p className="hint" style={{ marginBottom: "0.75rem" }}>
          Mode: <strong>Autonomous</strong> (ReAct)
        </p>
        {agentTrace.map((t, idx) => {
          const toolIdx = t.step_type === "observation" ? getObservationToolIndex(idx) : -1;
          const tool = toolIdx >= 0 ? toolSequence[toolIdx] : null;
          return (
            <details key={`${t.step_index}-${t.step_type}-${idx}`} className="collapse sequence-step" style={{ animationDelay: `${idx * 0.05}s` }} open={t.step_index === 1}>
              <summary>
                <span className="step">Step {t.step_index}</span>
                {tool && <span className="tool-icon">{TOOL_ICONS[tool.tool] ?? "🔧"}</span>}
                <span className="tool">{stepLabel(t)}</span>
                {tool && (
                  <>
                    <span className={`badge ${tool.status === "success" ? "ok" : "fail"}`}>{tool.status}</span>
                    <span className="attempts">attempts: {tool.attempts}</span>
                  </>
                )}
              </summary>
              <div className="trace-block">
                {Object.keys(t.detail || {}).length > 0 && (
                  <div>
                    <strong>Detail:</strong>
                    <pre>{JSON.stringify(t.detail, null, 2)}</pre>
                  </div>
                )}
                {tool && (
                  <>
                    <div>
                      <strong>Args:</strong>
                      <pre>{JSON.stringify(tool.args, null, 2)}</pre>
                    </div>
                    {tool.error && (
                      <div>
                        <strong>Error:</strong>
                        <pre>{tool.error}</pre>
                      </div>
                    )}
                    <div>
                      <strong>Result:</strong>
                      <pre>{JSON.stringify(tool.result, null, 2)}</pre>
                    </div>
                  </>
                )}
              </div>
            </details>
          );
        })}
      </div>
    );
  }

  if (!toolSequence.length) {
    return <p className="hint">No agent tool sequence available for this response.</p>;
  }

  return (
    <div className="sequence">
      {result.agent_mode === "deterministic" && (
        <p className="hint" style={{ marginBottom: "0.75rem" }}>
          Mode: <strong>Deterministic</strong> (fixed pipeline)
        </p>
      )}
      {toolSequence.map((item, idx) => (
        <details key={`${item.step}-${item.tool}`} className="collapse sequence-step" style={{ animationDelay: `${idx * 0.05}s` }} open={item.step === 1}>
          <summary>
            <span className="step">Step {item.step}</span>
            <span className="tool-icon">{TOOL_ICONS[item.tool] ?? "🔧"}</span>
            <span className="tool">{item.tool}</span>
            <span className={`badge ${item.status === "success" ? "ok" : "fail"}`}>{item.status}</span>
            <span className="attempts">attempts: {item.attempts}</span>
          </summary>
          <div className="trace-block">
            <div>
              <strong>Args:</strong>
              <pre>{JSON.stringify(item.args, null, 2)}</pre>
            </div>
            {item.error && (
              <div>
                <strong>Error:</strong>
                <pre>{item.error}</pre>
              </div>
            )}
            <div>
              <strong>Result:</strong>
              <pre>{JSON.stringify(item.result, null, 2)}</pre>
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}

export default App;
