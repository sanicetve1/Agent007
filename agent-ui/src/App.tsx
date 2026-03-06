import React, { useState } from "react";
import "./App.css";

type TraceStep = {
  step: string;
  info: Record<string, any>;
};

type RunResponse = {
  trace: TraceStep[];
  final_response: string;
};

const API_URL = "http://localhost:8000/agent/run";

function App() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RunResponse | null>(null);

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input }),
      });
      if (!resp.ok) {
        throw new Error(`API error: ${resp.status}`);
      }
      const data: RunResponse = await resp.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Agent007 – Agent Flow Viewer</h1>
        <p>Visualize the LLM + tools execution loop (no chain-of-thought).</p>
      </header>

      <main className="app-main">
        <section className="panel panel-input">
          <form onSubmit={handleRun}>
            <label className="label">
              Instruction
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={'e.g. "divide 10 by 2 and subtract 3"'}
                rows={4}
              />
            </label>
            <button type="submit" disabled={loading || !input.trim()}>
              {loading ? "Running…" : "Run Agent"}
            </button>
          </form>
          {error && <div className="error">{error}</div>}
          {result && (
            <div className="final-answer">
              <h2>Final Answer</h2>
              <p>{result.final_response}</p>
            </div>
          )}
        </section>

        <section className="panel panel-flow">
          <h2>Execution Flow</h2>
          {!result && <p className="hint">Run the agent to see the flow diagram.</p>}
          {result && <FlowDiagram trace={result.trace} />}
        </section>
      </main>
    </div>
  );
}

type FlowDiagramProps = {
  trace: TraceStep[];
};

const STEP_LABELS: Record<string, string> = {
  received_input: "User Input",
  tools_available: "Tools Available",
  tool_selected: "Tool Selected",
  tool_executed: "Tool Executed",
  tool_error: "Tool Error",
  no_tool_used: "Agent Answer (No Tool)",
  final_response: "Final Response",
  input_guard_error: "Input Blocked",
};

const STEP_GROUP: Record<string, "input" | "agent" | "tool" | "final" | "other"> = {
  received_input: "input",
  tools_available: "agent",
  tool_selected: "agent",
  no_tool_used: "agent",
  tool_executed: "tool",
  tool_error: "tool",
  final_response: "final",
  input_guard_error: "other",
};

function FlowDiagram({ trace }: FlowDiagramProps) {
  return (
    <div className="flow-diagram">
      {trace.map((step, idx) => {
        const group = STEP_GROUP[step.step] ?? "other";
        return (
          <div className="flow-row" key={idx}>
            <div className={`flow-node flow-node-${group}`}>
              <div className="flow-node-title">
                {STEP_LABELS[step.step] ?? step.step}
              </div>
              <div className="flow-node-body">{renderStepBody(step)}</div>
            </div>
            {idx < trace.length - 1 && <div className="flow-arrow">↓</div>}
          </div>
        );
      })}
    </div>
  );
}

function renderStepBody(step: TraceStep) {
  const info = step.info || {};
  switch (step.step) {
    case "received_input":
      return <code>{info.user_input}</code>;
    case "tool_selected":
      return (
        <div>
          <div>
            <strong>Tool:</strong> {info.tool_name}
          </div>
          <div>
            <strong>Args:</strong> <code>{JSON.stringify(info.tool_args)}</code>
          </div>
        </div>
      );
    case "tool_executed":
      return (
        <div>
          <div>
            <strong>Tool:</strong> {info.tool_name}
          </div>
          <div>
            <strong>Args:</strong> <code>{JSON.stringify(info.tool_args)}</code>
          </div>
          <div>
            <strong>Result:</strong> <code>{String(info.tool_result)}</code>
          </div>
        </div>
      );
    case "tool_error":
    case "input_guard_error":
      return <div className="error">{info.error}</div>;
    case "no_tool_used":
    case "final_response":
      return <p>{info.response}</p>;
    default:
      return <pre>{JSON.stringify(info, null, 2)}</pre>;
  }
}

export default App;

