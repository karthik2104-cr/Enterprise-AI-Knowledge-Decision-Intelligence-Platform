import { FormEvent, useState } from "react";
import { api } from "../services/api";
import type { SearchHit } from "../types";
import { Empty, ErrorState, Loading } from "../components/States";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [document_type, setType] = useState("");
  const [department, setDept] = useState("");
  const [year, setYear] = useState("");
  const [section, setSection] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await api.search({
        query,
        document_type: document_type || null,
        department: department || null,
        year: year ? Number(year) : null,
        section: section || null,
      });
      setHits(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h2 className="page-title">Search</h2>
      <p className="lede">Hybrid retrieval with metadata filters, independent of Ask AI.</p>
      <form className="panel stack" onSubmit={onSubmit}>
        <label>
          Query
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="employee leave policy" required />
        </label>
        <div className="row">
          <label>
            Document type
            <input value={document_type} onChange={(e) => setType(e.target.value)} />
          </label>
          <label>
            Department
            <input value={department} onChange={(e) => setDept(e.target.value)} />
          </label>
          <label>
            Year
            <input value={year} onChange={(e) => setYear(e.target.value)} />
          </label>
          <label>
            Section
            <input value={section} onChange={(e) => setSection(e.target.value)} />
          </label>
          <button className="btn align-end" disabled={busy}>Search</button>
        </div>
      </form>
      {error && <ErrorState message={error} />}
      {busy && <Loading label="Searching…" />}
      {hits && hits.length === 0 && <Empty title="No matches" body="Try a broader query or clear filters." />}
      {hits && hits.length > 0 && (
        <div className="table-wrap mt">
          <table>
            <thead>
              <tr>
                <th>Document</th><th>Page</th><th>Section</th><th>Snippet</th><th>Score</th>
              </tr>
            </thead>
            <tbody>
              {hits.map((h) => (
                <tr key={h.chunk_id}>
                  <td>{h.document_name}</td>
                  <td>{h.page ?? "—"}</td>
                  <td>{h.section ?? "—"}</td>
                  <td>{h.snippet}</td>
                  <td>
                    {h.score.toFixed(3)}
                    <div className="muted">{h.score_explanation}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
