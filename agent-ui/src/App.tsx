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
  const [result, setResult] = useState<any>(null);

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
            <h2>Tool Tests</h2>
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
          </div>

          <div className="action-group">
            <h2>Use Cases</h2>
            <div className="button-row">
              <button onClick={runUseCasePreScreen} disabled={loading || !selectedApplicant}>
                Pre-screen (agent run)
              </button>
              <button onClick={runUseCaseFull} disabled={loading || !selectedApplicant}>
                Full underwriting
              </button>
            </div>
          </div>

          {error && <div className="error">{error}</div>}
        </section>

        <section className="panel results">
          <h2>Result</h2>
          {!result && <p className="hint">Run a tool or use-case to see output.</p>}
          {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
        </section>
      </main>
    </div>
  );
}

export default App;

