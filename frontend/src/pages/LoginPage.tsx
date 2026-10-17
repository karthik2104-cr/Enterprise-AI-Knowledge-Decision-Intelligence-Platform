import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../services/api";
import { ErrorState } from "../components/States";

export default function LoginPage() {
  const [email, setEmail] = useState("analyst@northwind-demo.com");
  const [password, setPassword] = useState("DemoPass123!");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      setToken(res.access_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <form className="login-panel stack" onSubmit={onSubmit}>
        <div>
          <p className="eyebrow">Northwind Intelligence</p>
          <h2 className="login-title">Sign in</h2>
          <p className="muted">Demo environment. Credentials are sample-only.</p>
        </div>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoComplete="username" />
        </label>
        <label>
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required autoComplete="current-password" />
        </label>
        {error && <ErrorState message={error} />}
        <button className="btn" disabled={busy}>
          {busy ? "Signing in…" : "Continue"}
        </button>
      </form>
      <aside className="login-aside">
        <h2>Knowledge operations console</h2>
        Grounded answers over policies and structured metrics, with retrieval, tools, verification, and evaluation.
        <ul>
          <li>Hybrid document retrieval</li>
          <li>Catalogued financial metrics</li>
          <li>Citations and latency metadata</li>
        </ul>
      </aside>
    </div>
  );
}
