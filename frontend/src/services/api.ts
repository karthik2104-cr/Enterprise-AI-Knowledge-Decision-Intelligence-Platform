const TOKEN_KEY = "eak_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    if (!path.includes("/api/auth/login")) {
      window.location.href = "/login";
    }
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ full_name: string; email: string; role: string }>("/api/auth/me"),
  dashboard: () => request<import("../types").DashboardMetrics>("/api/dashboard"),
  documents: (q?: string) => request<import("../types").DocumentItem[]>(`/api/documents${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  document: (id: string) => request<Record<string, unknown>>(`/api/documents/${id}`),
  deleteDocument: (id: string) => request(`/api/documents/${id}`, { method: "DELETE" }),
  upload: (form: FormData) => request<import("../types").DocumentItem>("/api/documents", { method: "POST", body: form }),
  search: (payload: object) => request<import("../types").SearchHit[]>("/api/search", { method: "POST", body: JSON.stringify(payload) }),
  ask: (question: string) =>
    request<import("../types").StructuredAnswer>("/api/ask", { method: "POST", body: JSON.stringify({ question }) }),
  analyze: (question: string) =>
    request<import("../types").StructuredAnswer>("/api/analyze", { method: "POST", body: JSON.stringify({ question }) }),
  report: (question: string) =>
    request<import("../types").ReportItem>("/api/report", { method: "POST", body: JSON.stringify({ question }) }),
  reports: () => request<import("../types").ReportItem[]>("/api/reports"),
  history: () => request<import("../types").HistoryItem[]>("/api/history"),
  historyItem: (id: string) => request<Record<string, unknown>>(`/api/history/${id}`),
  evaluationRuns: () => request<Record<string, unknown>[]>("/api/evaluation"),
  evaluationRun: () => request<Record<string, unknown>>("/api/evaluation/run", { method: "POST" }),
  evaluationResults: (runId?: string) =>
    request<Record<string, unknown>[]>(`/api/evaluation/results${runId ? `?run_id=${runId}` : ""}`),
};
