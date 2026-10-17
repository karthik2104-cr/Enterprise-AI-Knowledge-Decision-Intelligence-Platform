import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../services/api";
import type { HistoryItem } from "../types";
import { Empty, ErrorState, Loading } from "../components/States";

export default function HistoryPage() {
  const { id } = useParams();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .history()
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (id) api.historyItem(id).then(setDetail).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (loading) return <Loading label="Loading history…" />;
  if (!items.length && !id) {
    return (
      <div>
        <h2 className="page-title">History</h2>
        <Empty title="No interactions yet" body="Questions from Ask AI and Analysis appear here." />
      </div>
    );
  }

  const sources = Array.isArray(detail?.sources) ? (detail?.sources as { document?: string; page?: number }[]) : [];

  return (
    <div>
      <h2 className="page-title">History</h2>
      <p className="lede">Prior questions, summaries, sources, and tools.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Question</th>
              <th>Summary</th>
              <th>Tools</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td className="muted">{item.created_at ? new Date(item.created_at).toLocaleString() : ""}</td>
                <td>
                  <Link to={`/history/${item.id}`}>{item.question}</Link>
                </td>
                <td>{item.answer_summary}</td>
                <td>{item.tools_used.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {id && !detail && <Loading />}
      {detail && (
        <section className="panel mt">
          <h3>{String(detail.question)}</h3>
          <p className="answer">{String(detail.answer || "")}</p>
          <p className="muted">
            Sources: {sources.length ? sources.map((s) => `${s.document}${s.page ? ` p.${s.page}` : ""}`).join("; ") : "None"}
          </p>
        </section>
      )}
    </div>
  );
}
