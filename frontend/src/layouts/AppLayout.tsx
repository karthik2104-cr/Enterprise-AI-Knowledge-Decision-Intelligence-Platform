import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearToken } from "../services/api";

const links = [
  ["/", "Dashboard"],
  ["/ask", "Ask AI"],
  ["/documents", "Documents"],
  ["/search", "Search"],
  ["/analysis", "Analysis"],
  ["/reports", "Reports"],
  ["/evaluation", "Evaluation"],
  ["/history", "History"],
  ["/settings", "Settings"],
];

export default function AppLayout({ user }: { user?: { full_name: string; email: string } }) {
  const navigate = useNavigate();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>Northwind Intelligence</h1>
          <p>Knowledge &amp; decision platform</p>
        </div>
        <nav className="nav">
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="user">
          <div>{user?.full_name}</div>
          <div>{user?.email}</div>
          <button
            className="btn secondary"
            style={{ marginTop: 10, width: "100%" }}
            onClick={() => {
              clearToken();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
