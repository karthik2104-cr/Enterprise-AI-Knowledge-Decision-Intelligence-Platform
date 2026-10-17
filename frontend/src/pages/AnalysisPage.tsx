import { FormEvent, useState } from "react";
import AnswerPanel from "../components/AnswerPanel";
import { ErrorState, Loading } from "../components/States";
import { api } from "../services/api";
import type { StructuredAnswer } from "../types";

export default function AnalysisPage() {
  const [question, setQuestion] = useState("Analyze the company's Q3 performance and identify major changes.");
  const [data, setData] = useState<StructuredAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setData(await api.analyze(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="page-title">Analysis</h2>
      <p className="lede">Analytical questions that may combine documents, metrics, and calculations.</p>
      <form className="panel stack" onSubmit={onSubmit}>
        <label>
          Analysis question
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
        </label>
        <button className="btn" disabled={busy}>{busy ? "Analyzing…" : "Run analysis"}</button>
      </form>
      {error && <ErrorState message={error} />}
      {busy && <Loading />}
      {data && !busy && (
        <div className="mt">
          <AnswerPanel data={data} />
          {data.retrieval && (
            <div className="panel mt-sm">
              <h3>Plan</h3>
              <p className="muted">Tools and intent chosen for this analysis. Hidden model reasoning is not shown.</p>
              <div className="chips">
                {(((data.retrieval as { plan?: { intent?: string; tools?: string[] } }).plan || {}).tools || []).map((t) => (
                  <span className="chip" key={t}>{t}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
