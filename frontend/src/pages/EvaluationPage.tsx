import { useEffect, useState } from "react";
import { api } from "../services/api";
import { Empty, ErrorState, Loading } from "../components/States";

export default function EvaluationPage() {
  const [runs, setRuns] = useState<Record<string, unknown>[]>([]);
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setRuns(await api.evaluationRuns());
      setResults(await api.evaluationResults());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load evaluation");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await api.evaluationRun();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }

  const latest = runs[0];
  const metrics = (latest?.metrics || {}) as Record<string, number>;

  return (
    <div>
      <h2 className="page-title">Evaluation</h2>
      <p className="lede">Heuristic retrieval and generation metrics on the golden question set.</p>
      <button className="btn" onClick={run} disabled={busy}>{busy ? "Running…" : "Run evaluation"}</button>
      {error && <ErrorState message={error} />}
      {busy && <Loading label="Scoring retrieval and answers…" />}
      {latest && (
        <div className="grid-4" style={{ marginTop: 16 }}>
          {["precision_at_5", "recall_at_5", "mrr", "ndcg_at_5", "answer_correctness", "groundedness", "citation_correctness", "avg_latency_ms"].map((key) => (
            <div className="card" key={key}>
              <h3>{key.replaceAll("_", " ")}</h3>
              <div className="metric" style={{ fontSize: 22 }}>{metrics[key] ?? "—"}</div>
            </div>
          ))}
        </div>
      )}
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Per-question results</h3>
        {results.length === 0 ? (
          <Empty title="No results" body="Run evaluation to score the sample questions." />
        ) : (
          <table>
            <thead>
              <tr><th>Question</th><th>Pass</th><th>P@5</th><th>Recall</th><th>Correct</th><th>Grounded</th></tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const m = (r.metrics || {}) as Record<string, number>;
                return (
                  <tr key={String(r.id)}>
                    <td>{String(r.question)}</td>
                    <td><span className={`badge ${r.passed ? "indexed" : "failed"}`}>{r.passed ? "pass" : "fail"}</span></td>
                    <td>{m.precision_at_5}</td>
                    <td>{m.recall_at_5}</td>
                    <td>{m.answer_correctness}</td>
                    <td>{m.groundedness}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
