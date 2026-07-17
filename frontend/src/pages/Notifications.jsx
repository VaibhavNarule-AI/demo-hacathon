import { useEffect, useState } from "react";
import api from "../services/api";

function fmtDate(iso) {
  if (!iso) return "—";
  return iso.replace("T", " ").slice(0, 16);
}

const TABS = [
  { key: "emails", label: "Email Outbox" },
  { key: "teams", label: "Teams Outbox" },
  { key: "bell", label: "Bell History" },
];

export default function Notifications() {
  const [tab, setTab] = useState("emails");
  const [rows, setRows] = useState({ emails: null, teams: null, bell: null });
  const [loading, setLoading] = useState(true);

  function load(key) {
    const endpoint = key === "emails" ? "/notifications/emails" : key === "teams" ? "/notifications/teams" : "/notifications/list";
    setLoading(true);
    api
      .get(endpoint)
      .then((res) => setRows((r) => ({ ...r, [key]: res.data })))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (rows[tab] === null) load(tab);
    else setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const data = rows[tab] || [];

  return (
    <div className="table-card">
      <div style={{ display: "flex", gap: "0.5rem", padding: "1rem 1.2rem 0" }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`btn ${tab === t.key ? "" : "secondary"}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ padding: "1rem 1.2rem 1.4rem" }}>
        {loading ? (
          <div className="loading-state">Loading…</div>
        ) : data.length === 0 ? (
          <div className="empty-state">
            {tab === "emails" && "No emails sent yet — trigger a Critical incident or wait for the 60s auto-escalation loop."}
            {tab === "teams" && "No Teams alerts sent yet."}
            {tab === "bell" && "No notifications logged yet."}
          </div>
        ) : tab === "emails" ? (
          <table className="incident-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Subject</th>
                <th>To</th>
                <th>Sent</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((e) => (
                <tr key={e.id}>
                  <td className="mono">{e.ticket_number}</td>
                  <td>{e.subject}</td>
                  <td>{e.to_email}</td>
                  <td className="mono">{fmtDate(e.sent_at)}</td>
                  <td><span className="badge Matched">{e.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : tab === "teams" ? (
          <table className="incident-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Partner</th>
                <th>Webhook (mock)</th>
                <th>Sent</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.map((t) => (
                <tr key={t.id}>
                  <td className="mono">{t.ticket_number}</td>
                  <td>{t.partner_id}</td>
                  <td className="mono">{t.webhook_url_mock}</td>
                  <td className="mono">{fmtDate(t.created_at)}</td>
                  <td><span className="badge Matched">{t.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="incident-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Type</th>
                <th>Message</th>
                <th>Logged</th>
              </tr>
            </thead>
            <tbody>
              {data.map((n) => (
                <tr key={n.id}>
                  <td className="mono">{n.ticket_number}</td>
                  <td><span className="badge">{n.type}</span></td>
                  <td>{n.message}</td>
                  <td className="mono">{fmtDate(n.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
