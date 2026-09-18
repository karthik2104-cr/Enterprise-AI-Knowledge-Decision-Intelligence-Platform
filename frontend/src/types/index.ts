export type StructuredAnswer = {
  answer: string;
  confidence: number;
  claims: { text: string; evidence: Evidence[]; supported?: boolean }[];
  sources: Evidence[];
  uncertainty: string[];
  tools_used: string[];
  latency: {
    retrieval_ms: number;
    rerank_ms: number;
    llm_ms: number;
    verification_ms: number;
    total_ms: number;
  };
  verification: Record<string, unknown>;
  retrieval: Record<string, unknown>;
  query_id?: string;
  response_id?: string;
};

export type Evidence = {
  document: string;
  page?: number | null;
  section?: string | null;
  chunk_id?: string | null;
  snippet?: string | null;
  score?: number | null;
  retrieval_method?: string | null;
  citation_index?: number | null;
};

export type DocumentItem = {
  id: string;
  title: string;
  original_name: string;
  status: string;
  department?: string | null;
  doc_type?: string | null;
  year?: number | null;
  chunk_count: number;
  error_message?: string | null;
  ingested_ms?: number | null;
  created_at?: string | null;
};

export type SearchHit = {
  document_id: string;
  document_name: string;
  chunk_id: string;
  page?: number | null;
  section?: string | null;
  snippet: string;
  score: number;
  retrieval_method: string;
  score_explanation: string;
};

export type HistoryItem = {
  id: string;
  question: string;
  query_type: string;
  created_at?: string | null;
  answer_summary?: string | null;
  tools_used: string[];
  sources: string[];
  confidence?: number | null;
};

export type DashboardMetrics = {
  documents: number;
  indexed_documents: number;
  questions: number;
  reports: number;
  searches: number;
  evaluation_runs: number;
  recent_activity: { id: string; question: string; type: string; created_at?: string }[];
};

export type ReportItem = {
  id: string;
  title: string;
  question: string;
  status: string;
  content: Record<string, unknown>;
  created_at?: string | null;
};
