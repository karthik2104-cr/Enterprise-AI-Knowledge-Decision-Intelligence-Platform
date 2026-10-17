import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";
import type { ReportItem } from "../types";
import { Empty, ErrorState, Loading, Toast } from "../components/States";

function renderReport(content: Record<string, unknown>) {
  const sections = (content.sections || {}) as Record<string, unknown>;
  const order = ["executive_summary", "key_metrics", "major_changes", "analysis", "supporting_evidence", "sources"];
  const labels: Record<string, string> = {
    executive_summary: "Executive summary",
    key_metrics: "Key metrics",
    major_changes: "Major changes",
    analysis: "Analysis",
    supporting_evidence: "Supporting evidence",
    sources: "Sources",
  };
  return (
    <div className="stack">
      {order.map((key) => (
        <div key={key}>
          <h3>{labels[key]}</h3>
          {typeof sections[key] === "string" ? (
            <p className="answer">{String(sections[key])}</p>
          ) : (
            <pre className="json">{JSON.stringify(sections[key] ?? "—", null, 2)}</pre>
          )}
        </div>
      ))}
    </div>
  );
}

export default function ReportsPage() {
  const [question, setQuestion] = useState("Generate a report about Q3 performance.");
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [selected, setSelected] = useState<ReportItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  async function load() {
    try {
      setReports(await api.reports());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load reports");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const report = await api.report(question);
      setSelected(report);
      setToast("Report stored");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="page-title">Reports</h2>
      <p className="lede">Generate and store structured management reports.</p>
      <form className="panel stack" onSubmit={onSubmit}>
        <label>
          Report request
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
        </label>
        <button className="btn" disabled={busy}>{busy ? "Generating…" : "Generate report"}</button>
      </form>
      {error && <ErrorState message={error} />}
      {busy && <Loading label="Planning, retrieving, verifying, and writing the report…" />}
      <div className="panel mt">
        <h3>Stored reports</h3>
        {reports.length === 0 ? (
          <Empty title="No reports" body="Generate a Q3 performance report to populate this list." />
        ) : (
          <div className="table-wrap flat">
          <table>
            <thead><tr><th>Title</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td><button className="btn link" onClick={() => setSelected(r)}>{r.title}</button></td>
                  <td><span className={`badge ${r.status}`}>{r.status}</span></td>
                  <td className="muted">{r.created_at ? new Date(r.created_at).toLocaleString() : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
      {selected && (
        <div className="report-doc mt">
          <h3>{selected.title}</h3>
          {renderReport(selected.content)}
        </div>
      )}
      <Toast message={toast} />
    </div>
  );
}
