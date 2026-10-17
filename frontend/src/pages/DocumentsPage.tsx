import { FormEvent, useEffect, useState } from "react";
import { api } from "../services/api";
import type { DocumentItem } from "../types";
import { Empty, ErrorState, Loading, Toast } from "../components/States";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function load(query?: string) {
    setBusy(true);
    try {
      setDocs(await api.documents(query));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    try {
      await api.upload(form);
      setToast("Document ingested");
      e.currentTarget.reset();
      await load(q);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <div>
      <h2 className="page-title">Documents</h2>
      <p className="lede">Upload, inspect ingestion status, and review chunks.</p>
      <form className="panel row mb" onSubmit={onUpload}>
        <label>
          File
          <input name="file" type="file" required />
        </label>
        <label>
          Department
          <input name="department" className="w-dept" placeholder="Optional" />
        </label>
        <label>
          Type
          <input name="doc_type" className="w-type" placeholder="Optional" />
        </label>
        <label>
          Year
          <input name="year" className="w-year" placeholder="Optional" />
        </label>
        <button className="btn align-end">Upload</button>
      </form>
      <div className="row mb-sm">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by title" className="w-filter" />
        <button className="btn secondary" onClick={() => load(q)}>Filter</button>
      </div>
      {error && <ErrorState message={error} />}
      {busy ? (
        <Loading />
      ) : docs.length === 0 ? (
        <Empty title="No documents" body="Upload a PDF, DOCX, TXT, or Markdown file." />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Title</th><th>Status</th><th>Dept</th><th>Type</th><th>Chunks</th><th>Ingest ms</th><th></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>
                    <button className="btn link" onClick={async () => setSelected(await api.document(d.id))}>{d.title}</button>
                    {d.error_message && <div className="muted">{d.error_message}</div>}
                  </td>
                  <td><span className={`badge ${d.status}`}>{d.status}</span></td>
                  <td>{d.department || "—"}</td>
                  <td>{d.doc_type || "—"}</td>
                  <td className="num">{d.chunk_count}</td>
                  <td className="num">{d.ingested_ms ?? "—"}</td>
                  <td>
                    <button className="btn danger" onClick={async () => { await api.deleteDocument(d.id); await load(q); }}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {selected && (
        <section className="panel mt">
          <h3>Document details</h3>
          <pre className="json">{JSON.stringify(selected, null, 2)}</pre>
        </section>
      )}
      <Toast message={toast} />
    </div>
  );
}
