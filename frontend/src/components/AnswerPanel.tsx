import type { StructuredAnswer } from "../types";

export default function AnswerPanel({ data }: { data: StructuredAnswer }) {
  const v = data.verification || {};
  return (
    <div className="stack">
      <section className="result-block">
        <h3 className="section-title">Answer</h3>
        <div className="answer">{data.answer}</div>
      </section>
      <dl className="meta-grid">
        <div>
          <dt>Confidence</dt>
          <dd>{(data.confidence * 100).toFixed(0)}%</dd>
        </div>
        <div>
          <dt>Verification</dt>
          <dd>
            <span className={`badge ${String(v.status || "")}`}>{String(v.status || "n/a")}</span>
            <div className="muted muted-tight">
              Does not guarantee truth.
            </div>
          </dd>
        </div>
        <div>
          <dt>Latency</dt>
          <dd>
            {(data.latency.total_ms / 1000).toFixed(2)}s
            <div className="muted muted-tight">
              retrieval {data.latency.retrieval_ms.toFixed(0)}ms · rerank {data.latency.rerank_ms.toFixed(0)}ms ·
              generation {data.latency.llm_ms.toFixed(0)}ms
            </div>
          </dd>
        </div>
        <div>
          <dt>Tools</dt>
          <dd>
            <div className="chips">
              {data.tools_used.length ? (
                data.tools_used.map((t) => (
                  <span className="chip" key={t}>
                    {t}
                  </span>
                ))
              ) : (
                <span className="muted">None</span>
              )}
            </div>
          </dd>
        </div>
      </dl>
      {data.uncertainty.length > 0 && (
        <section>
          <h3 className="section-title">Uncertainty</h3>
          <ul>
            {data.uncertainty.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </section>
      )}
      <section>
        <h3 className="section-title">Evidence</h3>
        <p className="evidence-note">Retrieved chunks that support the answer. Distinct from generated text.</p>
        {data.sources.length === 0 ? (
          <p className="muted">No document evidence attached.</p>
        ) : (
          <div className="table-wrap">
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
                    <td className="num">{s.citation_index}</td>
                    <td>{s.document}</td>
                    <td>{s.page ?? "—"}</td>
                    <td>{s.section ?? "—"}</td>
                    <td>{s.snippet}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
