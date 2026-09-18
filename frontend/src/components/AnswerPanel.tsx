import type { StructuredAnswer } from "../types";

export default function AnswerPanel({ data }: { data: StructuredAnswer }) {
  const v = data.verification || {};
  return (
    <div className="stack">
      <div className="card">
        <h3>Answer</h3>
        <div className="answer">{data.answer}</div>
      </div>
      <div className="grid-4">
        <div className="card">
          <h3>Confidence</h3>
          <div className="metric">{(data.confidence * 100).toFixed(0)}%</div>
        </div>
        <div className="card">
          <h3>Verification</h3>
          <div className={`badge ${String(v.status || "")}`}>{String(v.status || "n/a")}</div>
          <p className="muted">Does not guarantee truth.</p>
        </div>
        <div className="card">
          <h3>Latency</h3>
          <div>{(data.latency.total_ms / 1000).toFixed(2)}s total</div>
          <p className="muted">
            retrieval {data.latency.retrieval_ms.toFixed(0)}ms · rerank {data.latency.rerank_ms.toFixed(0)}ms ·
            generation {data.latency.llm_ms.toFixed(0)}ms
          </p>
        </div>
        <div className="card">
          <h3>Tools used</h3>
          <div className="chips">
            {data.tools_used.length ? data.tools_used.map((t) => <span className="chip" key={t}>{t}</span>) : <span className="muted">None</span>}
          </div>
        </div>
      </div>
      {data.uncertainty.length > 0 && (
        <div className="card">
          <h3>Uncertainty</h3>
          <ul>
            {data.uncertainty.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="card">
        <h3>Evidence</h3>
        {data.sources.length === 0 ? (
          <p className="muted">No document evidence attached.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Document</th>
                <th>Page</th>
                <th>Section</th>
                <th>Snippet</th>
              </tr>
            </thead>
            <tbody>
              {data.sources.map((s) => (
                <tr key={s.chunk_id || s.citation_index}>
                  <td>{s.citation_index}</td>
                  <td>{s.document}</td>
                  <td>{s.page ?? "—"}</td>
                  <td>{s.section ?? "—"}</td>
                  <td>{s.snippet}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
