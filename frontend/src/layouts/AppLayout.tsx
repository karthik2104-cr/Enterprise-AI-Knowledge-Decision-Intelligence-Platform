import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { clearToken } from "../services/api";

const groups = [
  {
    label: "Workspace",
    links: [
      ["/", "Dashboard"],
      ["/documents", "Documents"],
      ["/search", "Search"],
    ],
  },
  {
    label: "Intelligence",
    links: [
      ["/ask", "Ask AI"],
      ["/analysis", "Analysis"],
      ["/reports", "Reports"],
    ],
  },
  {
    label: "Operations",
    links: [
      ["/evaluation", "Evaluation"],
      ["/history", "History"],
      ["/settings", "Settings"],
    ],
  },
];

const titles: Record<string, string> = {
  "/": "Operations overview",
  "/ask": "Grounded question answering",
  "/documents": "Knowledge base",
  "/search": "Hybrid retrieval",
  "/analysis": "Analytical workspace",
  "/reports": "Generated reports",
  "/evaluation": "Retrieval & generation eval",
  "/history": "Interaction history",
  "/settings": "Runtime configuration",
};

export default function AppLayout({ user }: { user?: { full_name: string; email: string } }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const context = titles[location.pathname] || (location.pathname.startsWith("/history") ? "Interaction history" : "Workspace");

  return (
    <div className="app-shell">
      <div className={`scrim ${open ? "open" : ""}`} onClick={() => setOpen(false)} />
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <h1>Northwind Intelligence</h1>
          <p>Knowledge &amp; decision operations</p>
        </div>
        <nav className="nav" onClick={() => setOpen(false)}>
          {groups.map((group) => (
            <div key={group.label}>
              <span className="nav-label">{group.label}</span>
              {group.links.map(([to, label]) => (
                <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="user">
          <div className="name">{user?.full_name}</div>
          <div>{user?.email}</div>
          <button
            className="btn secondary btn-block"
            onClick={() => {
              clearToken();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button type="button" className="menu-btn" onClick={() => setOpen(true)} aria-label="Open navigation">
            Menu
          </button>
          <span>{context}</span>
          <span className="muted">{user?.email}</span>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
