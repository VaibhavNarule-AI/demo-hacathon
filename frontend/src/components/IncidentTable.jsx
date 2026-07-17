import { useState } from "react";
import api from "../services/api";

const RECOMMENDATIONS = {
  Phishing: "Block sender domain, force password reset for the targeted mailbox, and re-run the phishing awareness module for the affected user.",
  Malware: "Isolate the endpoint, run a full AV/EDR scan, and validate the sample hash against threat intel before re-imaging.",
  "Brute Force": "Enforce account lockout / MFA on the targeted account and block the source IP range at the perimeter.",
  "Data Exfiltration": "Suspend the account, snapshot the affected host for forensics, and notify the customer's data protection owner.",
  "Privilege Escalation": "Revoke the elevated token, audit recent group membership changes, and rotate any credentials the account touched.",
  "Suspicious Login": "Confirm with the user, force re-authentication with MFA, and geo-fence the account if the login was out of region.",
  "Lateral Movement": "Segment the affected subnet, hunt for the technique's related MITRE IDs across the environment, and rotate local admin credentials.",
  "C2 Beacon": "Null-route the C2 destination at DNS/firewall, isolate the host, and hunt for the same indicator across the fleet.",
};

function fmtDate(iso) {
  if (!iso) return "—";
  return iso.replace("T", " ").slice(0, 16);
}

export default function IncidentTable({ incidents, loading }) {
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState("");

  async function openDetail(id) {
    setDetailError("");
    try {
      const res = await api.get(`/incidents/${id}`);
      setDetail(res.data);
    } catch (err) {
      setDetailError(err.response?.data?.detail || "Could not load incident.");
    }
  }

  return (
    <div className="table-card">
      <h3>Incidents (drill-down)</h3>
      {loading ? (
        <div className="loading-state">Loading incidents…</div>
      ) : incidents.length === 0 ? (
        <div className="empty-state">No incidents match the current filters.</div>
      ) : (
        <table className="incident-table">
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Customer</th>
              <th>Severity</th>
              <th>SLA</th>
              <th>Created</th>
              <th>Analyst</th>
            </tr>
          </thead>
          <tbody>
            {incidents.slice(0, 50).map((inc) => (
              <tr key={inc.id} onClick={() => openDetail(inc.id)}>
                <td className="mono">{inc.ticket_number}</td>
                <td>{inc.customer}</td>
                <td>
                  <span className={`badge ${inc.severity}`}>{inc.severity}</span>
                </td>
                <td>
                  <span className={`badge ${inc.sla_result}`}>{inc.sla_result}</span>
                </td>
                <td className="mono">{fmtDate(inc.created_time)}</td>
                <td>{inc.assigned_analyst || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {(detail || detailError) && (
        <div className="modal-backdrop" onClick={() => { setDetail(null); setDetailError(""); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            {detailError ? (
              <div className="error-state">{detailError}</div>
            ) : (
              <>
                <h3>{detail.ticket_number}</h3>
                <dl>
                  <dt>Customer</dt>
                  <dd>{detail.customer} ({detail.partner})</dd>
                  <dt>Severity</dt>
                  <dd><span className={`badge ${detail.severity}`}>{detail.severity}</span></dd>
                  <dt>Status</dt>
                  <dd>{detail.status}</dd>
                  <dt>SLA Result</dt>
                  <dd><span className={`badge ${detail.sla_result}`}>{detail.sla_result}</span></dd>
                  <dt>SIEM / SOAR</dt>
                  <dd>{detail.siem} / {detail.soar}</dd>
                  <dt>Category</dt>
                  <dd>{detail.category}</dd>
                  <dt>Summary</dt>
                  <dd>{detail.summary}</dd>
                  <dt>MITRE Techniques</dt>
                  <dd>{detail.mitre_techniques}</dd>
                  <dt>Assigned Analyst</dt>
                  <dd>{detail.assigned_analyst || "Unassigned"}</dd>
                  <dt>Event → Created</dt>
                  <dd>{fmtDate(detail.event_time)} → {fmtDate(detail.created_time)}</dd>
                  <dt>Opened → Closed</dt>
                  <dd>{fmtDate(detail.opened_time)} → {fmtDate(detail.closed_time)}</dd>
                  <dt>Recommendation</dt>
                  <dd>{RECOMMENDATIONS[detail.category] || "Triage per standard playbook for this category."}</dd>
                </dl>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
