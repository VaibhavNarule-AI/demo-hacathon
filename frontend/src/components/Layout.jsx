import { useNavigate } from "react-router-dom";

export default function Layout({ title, latencyMs, children }) {
  const navigate = useNavigate();
  const role = localStorage.getItem("role") || "unknown";
  const partnerId = localStorage.getItem("partner_id") || "*";
  const customerId = localStorage.getItem("customer_id");
  const scope = customerId ? `${partnerId} / ${customerId}` : partnerId || "*";

  function logout() {
    localStorage.clear();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <h1>{title}</h1>
        <div className="actions">
          {role === "super_admin" && (
            <a className="btn secondary" href="/admin" style={{ textDecoration: "none" }}>
              Admin
            </a>
          )}
          <button className="btn secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </div>
      <div className="page-container">{children}</div>
      <div className="role-footer">
        Role: {role} | Scope: {scope} | Latency: {latencyMs !== null ? `${latencyMs}ms` : "—"}
      </div>
    </div>
  );
}
