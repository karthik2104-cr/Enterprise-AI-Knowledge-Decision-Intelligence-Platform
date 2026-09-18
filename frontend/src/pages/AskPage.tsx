import { FormEvent, useState } from "react";
import AnswerPanel from "../components/AnswerPanel";
import { ErrorState, Loading, Toast } from "../components/States";
import { api } from "../services/api";
import type { StructuredAnswer } from "../types";

const EXAMPLES = [
  "What is the company's leave policy?",
  "What was Q3 revenue?",
  "Compare Q2 and Q3 revenue.",
  "What changed in Q3?",
  "What are the major compliance requirements?",
  "Generate a Q3 performance report.",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [data, setData] = useState<StructuredAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function submit(q: string) {
    setBusy(true);
    setError(null);
    try {
      const wantsReport = q.toLowerCase().includes("generate") && q.toLowerCase().includes("report");
      if (wantsReport) {
        const report = await api.report(q);
        const nested = report.content.answer as StructuredAnswer | undefined;
        if (nested?.answer) setData(nested);
        else throw new Error("Report was stored but did not include a structured answer.");
      } else {
        setData(q.toLowerCase().includes("analyze") ? await api.analyze(q) : await api.ask(q));
      }
      setToast("Response generated");
      setTimeout(() => setToast(null), 1800);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (question.trim()) submit(question.trim());
  }

  return (
    <div>
      <h2 className="page-title">Ask AI</h2>
      <p className="lede">Grounded answers with citations, confidence, tools, and latency.</p>
      <form className="card stack" onSubmit={onSubmit}>
        <textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question about policies, finances, or operations" />
        <div className="row">
          <button className="btn" disabled={busy || !question.trim()}>{busy ? "Working…" : "Submit"}</button>
        </div>
        <div className="chips">
          {EXAMPLES.map((ex) => (
            <button type="button" className="chip" key={ex} onClick={() => { setQuestion(ex); submit(ex); }}>
              {ex}
            </button>
          ))}
        </div>
      </form>
      {error && <ErrorState message={error} />}
      {busy && <Loading label="Retrieving evidence and generating a structured answer…" />}
      {data && !busy && <div style={{ marginTop: 16 }}><AnswerPanel data={data} /></div>}
      <Toast message={toast} />
    </div>
  );
}
