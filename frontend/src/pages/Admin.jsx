import { useEffect, useState } from "react";
import api from "../services/api";

function fmtDate(iso) {
  if (!iso) return "—";
  return iso.replace("T", " ").slice(0, 19);
}

const TABS = [
  { key: "users", label: "Users" },
  { key: "audit", label: "Audit Logs" },
  { key: "flow", label: "Flow Log" },
  { key: "tests", label: "Test Report" },
];

export default function Admin() {
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState(null);
  const [auditLogs, setAuditLogs] = useState(null);
  const [flowLog, setFlowLog] = useState(null);
  const [resetStatus, setResetStatus] = useState("");

  useEffect(() => {
    if (tab === "users" && users === null) api.get("/admin/users").then((res) => setUsers(res.data)).catch(() => setUsers([]));
    if (tab === "audit" && auditLogs === null) api.get("/admin/audit-logs").then((res) => setAuditLogs(res.data)).catch(() => setAuditLogs([]));
    if (tab === "flow") api.get("/admin/flow-log", { responseType: "text" }).then((res) => setFlowLog(res.data)).catch(() => setFlowLog("Could not load flow.log"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function handleReset() {
    setResetStatus("Reseeding demo data…");
    try {
      await api.post("/demo/reset");
      setResetStatus("Demo data reseeded. Refresh the page to see the new data.");
      setUsers(null);
      setAuditLogs(null);
    } catch (err) {
      setResetStatus(err.response?.data?.detail || "Reset failed.");
    }
  }

  return (
    <>
      <div className="table-card" style={{ marginBottom: "1.4rem" }}>
        <h3>Demo controls</h3>
        <div style={{ padding: "0 1.2rem 1.2rem" }}>
          <button className="btn" onClick={handleReset}>
            Re-seed demo data
          </button>
          {resetStatus && <p style={{ color: "var(--text-soft)" }}>{resetStatus}</p>}
        </div>
      </div>

      <div className="table-card">
        <div style={{ display: "flex", gap: "0.5rem", padding: "1rem 1.2rem 0" }}>
          {TABS.map((t) => (
            <button key={t.key} className={`btn ${tab === t.key ? "" : "secondary"}`} onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          ))}
        </div>

        <div style={{ padding: "1rem 1.2rem 1.4rem" }}>
          {tab === "users" && (
            users === null ? (
              <div className="loading-state">Loading…</div>
            ) : (
              <table className="incident-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Partner</th>
                    <th>Customer</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.email}>
                      <td className="mono">{u.email}</td>
                      <td><span className="badge role-badge">{u.role}</span></td>
                      <td className="mono">{u.partner_id || "—"}</td>
                      <td className="mono">{u.customer_id || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}

          {tab === "audit" && (
            auditLogs === null ? (
              <div className="loading-state">Loading…</div>
            ) : auditLogs.length === 0 ? (
              <div className="empty-state">No audit log entries yet.</div>
            ) : (
              <table className="incident-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Tenant Filter</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((a) => (
                    <tr key={a.id}>
                      <td className="mono">{fmtDate(a.timestamp)}</td>
                      <td className="mono">{a.user}</td>
                      <td>{a.action}</td>
                      <td className="mono" style={{ fontSize: "0.72rem" }}>{a.tenant_filter}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}

          {tab === "flow" && (
            flowLog === null ? (
              <div className="loading-state">Loading…</div>
            ) : (
              <pre className="flow-log-viewer">{flowLog}</pre>
            )
          )}

          {tab === "tests" && (
            <iframe title="Test Report" src="/test-report" className="test-report-frame" />
          )}
        </div>
      </div>
    </>
  );
}
