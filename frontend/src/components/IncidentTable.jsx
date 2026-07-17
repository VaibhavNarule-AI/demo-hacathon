import { useMemo, useState } from "react";
import api from "../services/api";
import { errorMessage } from "../utils/errors";

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

const SEVERITY_ORDER = { Critical: 0, Major: 1, Minor: 2, Informational: 3 };
const PAGE_SIZE = 15;

const PRIORITY_CLASS = {
  "Critical Priority": "priority-critical",
  "High Priority": "priority-high",
  "Medium Priority": "priority-medium",
  "Low Priority": "priority-low",
};

function PriorityBadge({ score, label }) {
  if (score === null || score === undefined) return <span className="mono" style={{ color: "var(--text-faint)" }}>—</span>;
  return (
    <span className={`priority-badge ${PRIORITY_CLASS[label] || ""}`} title={label}>
      {score}
    </span>
  );
}

function fmtDate(iso) {
  if (!iso) return "—";
  return iso.replace("T", " ").slice(0, 16);
}

function Timeline({ detail }) {
  const steps = [
    { label: "Event", time: detail.event_time },
    { label: "Created", time: detail.created_time },
    { label: "Opened", time: detail.opened_time },
    { label: "First Response", time: detail.first_response_time },
    { label: "Closed", time: detail.closed_time },
  ];
  return (
    <div className="timeline-stepper">
      {steps.map((s, i) => (
        <div key={s.label} className={`timeline-step ${s.time ? "reached" : "pending"}`}>
          <div className="timeline-dot" />
          <div className="timeline-label">{s.label}</div>
          <div className="timeline-time">{fmtDate(s.time)}</div>
          {i < steps.length - 1 && <div className="timeline-connector" />}
        </div>
      ))}
    </div>
  );
}

const SNOOZE_OPTIONS = [
  { label: "15 min", mins: 15 },
  { label: "30 min", mins: 30 },
  { label: "1 hour", mins: 60 },
];

export default function IncidentTable({ incidents, loading, onRequestClose, onActionDone }) {
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState("");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("priority_score");
  const [sortDir, setSortDir] = useState("desc");
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState("details");
  const [emails, setEmails] = useState(null);
  const [teams, setTeams] = useState(null);
  const [actionStatus, setActionStatus] = useState("");
  const [acting, setActing] = useState(false);

  const filtered = useMemo(() => {
    let rows = incidents;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter((r) => r.ticket_number.toLowerCase().includes(q));
    }
    const sorted = [...rows].sort((a, b) => {
      let cmp;
      if (sortKey === "priority_score") {
        // Closed/never-opened incidents carry no priority score -- always
        // sink to the bottom regardless of sort direction, since they're
        // not part of "what should I work next" either way.
        if (a.priority_score === null && b.priority_score === null) cmp = 0;
        else if (a.priority_score === null) return 1;
        else if (b.priority_score === null) return -1;
        else cmp = a.priority_score - b.priority_score;
      } else if (sortKey === "severity") cmp = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
      else if (sortKey === "status") cmp = a.status.localeCompare(b.status);
      else cmp = a.created_time.localeCompare(b.created_time);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [incidents, search, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function toggleSort(key) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
    setPage(1);
  }

  async function openDetail(id) {
    setDetailError("");
    setTab("details");
    setEmails(null);
    setTeams(null);
    setActionStatus("");
    try {
      const res = await api.get(`/incidents/${id}`);
      setDetail(res.data);
    } catch (err) {
      setDetailError(errorMessage(err, "Could not load incident."));
    }
  }

  function closeDetail() {
    setDetail(null);
    setDetailError("");
  }

  async function openTab(nextTab) {
    setTab(nextTab);
    if (nextTab === "email" && emails === null) {
      try {
        const res = await api.get("/notifications/emails");
        setEmails(res.data.filter((e) => e.ticket_number === detail.ticket_number));
      } catch {
        setEmails([]);
      }
    }
    if (nextTab === "teams" && teams === null) {
      try {
        const res = await api.get("/notifications/teams");
        setTeams(res.data.filter((t) => t.ticket_number === detail.ticket_number));
      } catch {
        setTeams([]);
      }
    }
  }

  function requestResolve() {
    onRequestClose({
      incident_id: detail.id,
      ticket_number: detail.ticket_number,
      customer: detail.customer,
      severity: detail.severity,
      breaches_in: detail.status,
    });
    closeDetail();
  }

  async function snooze(mins) {
    setActing(true);
    setActionStatus("");
    try {
      await api.post(`/incidents/${detail.id}/snooze`, { mins });
      setActionStatus(`Snoozed for ${mins} min.`);
      onActionDone?.();
      const res = await api.get(`/incidents/${detail.id}`);
      setDetail(res.data);
    } catch (err) {
      setActionStatus(errorMessage(err, "Could not snooze."));
    } finally {
      setActing(false);
    }
  }

  async function sendEmail() {
    setActing(true);
    setActionStatus("");
    try {
      await api.post("/notifications/send-email", { ticket_number: detail.ticket_number, trigger_type: "Manual" });
      setActionStatus("Email sent to outbox.");
      setEmails(null);
    } catch (err) {
      setActionStatus(errorMessage(err, "Could not send email."));
    } finally {
      setActing(false);
    }
  }

  return (
    <div className="table-card">
      <div className="table-toolbar">
        <h3>Incidents (drill-down)</h3>
        <input
          className="table-search"
          placeholder="Search ticket number…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton-block" style={{ height: 40 }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          {incidents.length === 0
            ? "No incidents for this filter. Try expanding the date range or clearing a filter."
            : "No tickets match your search."}
        </div>
      ) : (
        <>
          <table className="incident-table">
            <thead>
              <tr>
                <th className="sortable" onClick={() => toggleSort("priority_score")}>
                  Priority {sortKey === "priority_score" && (sortDir === "asc" ? "▲" : "▼")}
                </th>
                <th>Ticket</th>
                <th>Customer</th>
                <th className="sortable" onClick={() => toggleSort("severity")}>
                  Severity {sortKey === "severity" && (sortDir === "asc" ? "▲" : "▼")}
                </th>
                <th className="sortable" onClick={() => toggleSort("status")}>
                  Status {sortKey === "status" && (sortDir === "asc" ? "▲" : "▼")}
                </th>
                <th>SLA</th>
                <th className="sortable" onClick={() => toggleSort("created_time")}>
                  Created {sortKey === "created_time" && (sortDir === "asc" ? "▲" : "▼")}
                </th>
                <th>Analyst</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((inc) => (
                <tr key={inc.id} onClick={() => openDetail(inc.id)}>
                  <td><PriorityBadge score={inc.priority_score} label={inc.priority_label} /></td>
                  <td className="mono">{inc.ticket_number}</td>
                  <td>{inc.customer}</td>
                  <td><span className={`badge ${inc.severity}`}>{inc.severity}</span></td>
                  <td><span className={`badge status-${inc.status}`}>{inc.status}</span></td>
                  <td><span className={`badge ${inc.sla_result}`}>{inc.sla_result}</span></td>
                  <td className="mono">{fmtDate(inc.created_time)}</td>
                  <td>{inc.assigned_analyst || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <button className="btn secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Prev
            </button>
            <span>
              Page {page} of {totalPages} ({filtered.length} incidents)
            </span>
            <button className="btn secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </>
      )}

      {(detail || detailError) && (
        <div className="modal-backdrop" onClick={closeDetail}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            {detailError ? (
              <div className="error-state">{detailError}</div>
            ) : (
              <>
                <h3>{detail.ticket_number}</h3>

                <div className="modal-tabs">
                  {["details", "timeline", "email", "teams"].map((t) => (
                    <button
                      key={t}
                      type="button"
                      className={`modal-tab ${tab === t ? "active" : ""}`}
                      onClick={() => openTab(t)}
                    >
                      {t === "email" ? "Email Outbox" : t === "teams" ? "Teams Outbox" : t[0].toUpperCase() + t.slice(1)}
                    </button>
                  ))}
                </div>

                {tab === "details" && (
                  <dl>
                    {detail.priority_score !== null && detail.priority_score !== undefined && (
                      <>
                        <dt>Smart Priority Score</dt>
                        <dd>
                          <span className={`priority-badge ${PRIORITY_CLASS[detail.priority_label] || ""}`}>
                            {detail.priority_score} / 100
                          </span>{" "}
                          <span style={{ color: "var(--text-soft)" }}>{detail.priority_label}</span>
                        </dd>
                        <dt>Reason</dt>
                        <dd>{detail.priority_reasons.join(" · ")}</dd>
                        <dt>Recommended Action</dt>
                        <dd><strong>{detail.recommended_action}</strong></dd>
                      </>
                    )}
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
                    <dt>Escalation Level</dt>
                    <dd>{detail.escalation_level || 0}</dd>
                    <dt>Recommendation</dt>
                    <dd>{RECOMMENDATIONS[detail.category] || "Triage per standard playbook for this category."}</dd>
                  </dl>
                )}

                {tab === "timeline" && <Timeline detail={detail} />}

                {tab === "email" && (
                  emails === null ? (
                    <div className="loading-state">Loading…</div>
                  ) : emails.length === 0 ? (
                    <div className="empty-state">No emails sent for this ticket yet.</div>
                  ) : (
                    emails.map((e) => (
                      <div key={e.id} className="outbox-item">
                        <div className="outbox-subject">{e.subject}</div>
                        <div className="outbox-meta">To: {e.to_email} · {fmtDate(e.sent_at)} · {e.status}</div>
                      </div>
                    ))
                  )
                )}

                {tab === "teams" && (
                  teams === null ? (
                    <div className="loading-state">Loading…</div>
                  ) : teams.length === 0 ? (
                    <div className="empty-state">No Teams alerts sent for this ticket yet.</div>
                  ) : (
                    teams.map((t) => {
                      let title = "Teams alert";
                      try {
                        title = JSON.parse(t.payload_json).title;
                      } catch {
                        /* keep default */
                      }
                      return (
                        <div key={t.id} className="outbox-item">
                          <div className="outbox-subject">{title}</div>
                          <div className="outbox-meta">{fmtDate(t.created_at)} · {t.status}</div>
                        </div>
                      );
                    })
                  )
                )}

                {actionStatus && <p style={{ color: "var(--text-soft)", fontSize: "0.85rem", marginTop: "0.8rem" }}>{actionStatus}</p>}

                {detail.status !== "Closed" && (
                  <div className="modal-actions">
                    {SNOOZE_OPTIONS.map((opt) => (
                      <button key={opt.mins} className="btn secondary" disabled={acting} onClick={() => snooze(opt.mins)}>
                        Snooze {opt.label}
                      </button>
                    ))}
                    <button className="btn secondary" disabled={acting} onClick={sendEmail}>
                      Send Email
                    </button>
                    <button className="btn" disabled={acting} onClick={requestResolve}>
                      Resolve
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
