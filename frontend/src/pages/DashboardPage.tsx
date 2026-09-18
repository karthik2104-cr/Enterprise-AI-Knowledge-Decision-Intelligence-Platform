import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { DashboardMetrics } from "../types";
import { Empty, ErrorState, Loading } from "../components/States";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboard().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loading label="Loading workspace metrics…" />;

  return (
    <div>
      <h2 className="page-title">Dashboard</h2>
      <p className="lede">Live counts from the knowledge base and interaction history.</p>
      <div className="grid-4">
        <div className="card"><h3>Documents</h3><div className="metric">{data.documents}</div><p className="muted">{data.indexed_documents} indexed</p></div>
        <div className="card"><h3>Questions</h3><div className="metric">{data.questions}</div></div>
        <div className="card"><h3>Reports</h3><div className="metric">{data.reports}</div></div>
        <div className="card"><h3>Searches</h3><div className="metric">{data.searches}</div><p className="muted">{data.evaluation_runs} eval runs</p></div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Recent activity</h3>
        {data.recent_activity.length === 0 ? (
          <Empty title="No questions yet" body="Ask a question from the Ask AI page to populate activity." />
        ) : (
          <table>
            <thead>
              <tr><th>Type</th><th>Question</th><th>When</th></tr>
            </thead>
            <tbody>
              {data.recent_activity.map((row) => (
                <tr key={row.id}>
                  <td><span className="badge">{row.type}</span></td>
                  <td><Link to={`/history/${row.id}`}>{row.question}</Link></td>
                  <td className="muted">{row.created_at ? new Date(row.created_at).toLocaleString() : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
