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
};

type AgentTraceStep = {
  step_index: number;
  step_type: string;
  detail: Record<string, any>;
};

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
  [k: string]: any;
};

const API_BASE = "http://localhost:8001";

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

  useEffect(() => {
    async function loadApplicants() {
      try {
        const resp = await fetch(`${API_BASE}/data/applicants`);
        if (!resp.ok) throw new Error(`Failed to load applicants (${resp.status})`);
        const data: Applicant[] = await resp.json();
        setApplicants(data);
        if (data.length > 0) setSelectedApplicant(data[0].applicant_id);
      } catch (err: any) {
        setError(err.message ?? "Failed to load applicants");
      }
    }
    loadApplicants();
  }, []);

  const selectedApplicantObject = useMemo(
    () => applicants.find((x) => x.applicant_id === selectedApplicant) || null,
    [applicants, selectedApplicant]
  );

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

  async function runCreditRisk() {
    setLoading(true);
    setError(null);
    try {
      const data = await callApi("/tools/calculate_credit_risk", { applicant_id: selectedApplicant });
      setResult(data);
    } catch (err: any) {
      setError(err.message ?? "Request failed");
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
      setError(err.message ?? "Request failed");
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
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function runCollateral() {
    if (!selectedLoan) {
      setError("Select a loan first.");
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
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function runUseCasePreScreen() {
    setLoading(true);
    setError(null);
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
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function runUseCaseFull() {
    setLoading(true);
    setError(null);
    try {
      const data = await callApi("/agent/run", {
        applicant_id: selectedApplicant,
        loan_id: selectedLoan || undefined,
        months,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  /** Start agent without applicant to trigger clarification (autonomy mode only). */
  async function runTestClarification() {
    setLoading(true);
    setError(null);
    setResult(null);
    setClarificationReply("");
    try {
      const data = await callApi("/agent/run", {
        applicant_id: null,
        months,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  /** Send reply after clarification_needed (e.g. paste applicant_id or answer in text). */
  async function sendClarificationReply() {
    const sessionId = result?.session_id;
    if (!sessionId || !clarificationReply.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await callApi("/agent/continue", {
        session_id: sessionId,
        user_reply: clarificationReply.trim(),
      });
      setResult(data);
      setClarificationReply("");
    } catch (err: any) {
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
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
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Loan Agent Tool Tester</h1>
        <p>Test underwriting tools and use-cases quickly.</p>
      </header>

      <main className="app-main">
        <section className="panel controls">
          <div className="field-grid">
            <label className="label">
              Applicant
              <select
                value={selectedApplicant}
                onChange={(e) => setSelectedApplicant(e.target.value)}
                disabled={loading || applicants.length === 0}
              >
                {applicants.map((a) => (
                  <option key={a.applicant_id} value={a.applicant_id}>
                    {a.full_name} ({a.applicant_id.slice(0, 8)}...)
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
              Threshold Ratio
              <input
                type="number"
                min={0.1}
                step={0.1}
                value={thresholdRatio}
                onChange={(e) => setThresholdRatio(Number(e.target.value))}
                disabled={loading}
              />
            </label>
            <label className="label">
              Loan
              <select value={selectedLoan} onChange={(e) => setSelectedLoan(e.target.value)} disabled={loading}>
                <option value="">Select loan</option>
                {loans.map((l) => (
                  <option key={l.loan_id} value={l.loan_id}>
                    {l.loan_type} - {l.outstanding_amount}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {selectedApplicantObject && (
            <div className="meta">
              Selected: <strong>{selectedApplicantObject.full_name}</strong> | Income:{" "}
              {selectedApplicantObject.annual_income} | KYC: {selectedApplicantObject.kyc_status}
            </div>
          )}

          <div className="action-group">
            <h2>Primary Flow</h2>
            <div className="button-row">
              <button onClick={runListLoans} disabled={loading || !selectedApplicant}>
                1. Fetch loans
              </button>
              <button onClick={runUseCaseFull} disabled={loading || !selectedApplicant}>
                2. Analyze applicant
              </button>
            </div>
          </div>

          <details className="action-group testing">
            <summary>Testing & debug tools</summary>
            <div className="testing-inner">
              <h3>Tool Tests</h3>
              <div className="button-row">
                <button onClick={runCreditRisk} disabled={loading || !selectedApplicant}>
                  calculate_credit_risk
                </button>
                <button onClick={runCashflow} disabled={loading || !selectedApplicant}>
                  analyze_cashflow
                </button>
                <button onClick={runListLoans} disabled={loading || !selectedApplicant}>
                  list_applicant_loans
                </button>
                <button onClick={runCollateral} disabled={loading || !selectedLoan}>
                  assess_collateral
                </button>
                <button onClick={runAllTools} disabled={loading || !selectedApplicant}>
                  Run All 3 Tools
                </button>
              </div>

              <h3>Use Cases</h3>
              <div className="button-row">
                <button onClick={runUseCasePreScreen} disabled={loading || !selectedApplicant}>
                  Pre-screen (agent run)
                </button>
                <button onClick={runUseCaseFull} disabled={loading || !selectedApplicant}>
                  Full underwriting
                </button>
                <button onClick={runTestClarification} disabled={loading}>
                  Test clarification (no applicant)
                </button>
              </div>
            </div>
          </details>

          {result?.status === "clarification_needed" && (
            <div className="meta" style={{ marginTop: "1rem", padding: "0.75rem", background: "#eff6ff", border: "1px solid #93c5fd", borderRadius: 8 }}>
              <p style={{ margin: "0 0 0.5rem", fontWeight: 600 }}>Agent asks for more information</p>
              <p style={{ margin: 0, fontSize: "0.9rem" }}>{result.clarification_question}</p>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Paste applicant_id (UUID) or type your answer"
                  value={clarificationReply}
                  onChange={(e) => setClarificationReply(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendClarificationReply()}
                  style={{ flex: 1, padding: "0.4rem 0.6rem" }}
                />
                <button onClick={sendClarificationReply} disabled={loading || !clarificationReply.trim()}>
                  Send reply
                </button>
              </div>
            </div>
          )}

          {error && <div className="error">{error}</div>}
        </section>

        <section className="panel results">
          <div className="results-header">
            <h2>Result</h2>
            <div className="tab-row">
              <button className={activeTab === "overview" ? "tab active" : "tab"} onClick={() => setActiveTab("overview")}>
                Overview
              </button>
              <button className={activeTab === "sequence" ? "tab active" : "tab"} onClick={() => setActiveTab("sequence")}>
                Agent Sequence
              </button>
              <button className={activeTab === "json" ? "tab active" : "tab"} onClick={() => setActiveTab("json")}>
                Raw JSON
              </button>
            </div>
          </div>

          {!result && <p className="hint">Run a tool or use-case to see output.</p>}
          {result?.status === "error" && (
            <div className="error">
              {result.message || result.error || "An error occurred."}
            </div>
          )}
          {result?.status === "clarification_needed" && (
            <p className="hint">Agent is waiting for your reply. Use the input in the left panel and click &quot;Send reply&quot; (or paste an applicant_id UUID to continue).</p>
          )}
          {result && result.status !== "clarification_needed" && result.status !== "error" && activeTab === "overview" && <OverviewTab result={result} />}
          {result && result.status !== "clarification_needed" && result.status !== "error" && activeTab === "sequence" && <SequenceTab result={result} />}
          {result && activeTab === "json" && <pre>{JSON.stringify(result, null, 2)}</pre>}
        </section>
      </main>
    </div>
  );
}

function OverviewTab({ result }: { result: AgentResult }) {
  const analysis = result.llm_outcome_analysis || {};
  const strengths = analysis.key_strengths || [];
  const risks = analysis.key_risks || [];
  const actions = analysis.next_actions || [];

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
          <div className="v">{analysis.decision || result.recommendation || "N/A"}</div>
        </div>
        <div className="summary-card">
          <div className="k">Overall Risk</div>
          <div className="v">{analysis.overall_risk_level || result.overall_risk_level || "N/A"}</div>
        </div>
        <div className="summary-card">
          <div className="k">Tool Failures</div>
          <div className="v">{result.tool_failed ? "Yes" : "No"}</div>
        </div>
      </div>

      <details open className="collapse">
        <summary>LLM Approval Summary</summary>
        <p>{analysis.approval_summary || result.explanation || "No summary available."}</p>
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
            <details key={`${t.step_index}-${t.step_type}-${idx}`} className="collapse" open={t.step_index === 1}>
              <summary>
                <span className="step">Step {t.step_index}</span>
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
      {toolSequence.map((item) => (
        <details key={`${item.step}-${item.tool}`} className="collapse" open={item.step === 1}>
          <summary>
            <span className="step">Step {item.step}</span>
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
