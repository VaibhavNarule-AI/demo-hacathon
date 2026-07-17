import { useState } from "react";
import api from "../services/api";

const SEVERITIES = ["Critical", "Major", "Minor", "Informational"];
const SIEMS = ["QRADAR", "XSIAM"];
const SOARS = ["XSOAR", "Resilient"];
const CATEGORIES = [
  "Phishing", "Malware", "Brute Force", "Data Exfiltration",
  "Privilege Escalation", "Suspicious Login", "Lateral Movement", "C2 Beacon",
];

export default function NewIncidentModal({ customers, onClose, onCreated }) {
  const fixedCustomer = localStorage.getItem("customer_id") || "";
  const [form, setForm] = useState({
    customer: fixedCustomer || customers[0]?.customer_id || "",
    severity: "Critical",
    category: CATEGORIES[0],
    summary: "",
    siem: SIEMS[0],
    soar: SOARS[0],
    assigned_analyst: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.post("/incidents/create", form);
      onCreated(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create incident.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>+ New Incident</h3>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
          <div>
            <label htmlFor="ni-customer">Customer</label>
            <select
              id="ni-customer"
              value={form.customer}
              onChange={(e) => set("customer", e.target.value)}
              disabled={!!fixedCustomer}
              required
            >
              {customers.map((c) => (
                <option key={c.customer_id} value={c.customer_id}>
                  {c.customer_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="ni-severity">Severity</label>
            <select id="ni-severity" value={form.severity} onChange={(e) => set("severity", e.target.value)}>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="ni-category">Category</label>
            <select id="ni-category" value={form.category} onChange={(e) => set("category", e.target.value)}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="ni-summary">Summary</label>
            <input
              id="ni-summary"
              value={form.summary}
              onChange={(e) => set("summary", e.target.value)}
              placeholder="Short description of what was detected"
              required
            />
          </div>
          <div style={{ display: "flex", gap: "0.9rem" }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="ni-siem">SIEM</label>
              <select id="ni-siem" value={form.siem} onChange={(e) => set("siem", e.target.value)}>
                {SIEMS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="ni-soar">SOAR</label>
              <select id="ni-soar" value={form.soar} onChange={(e) => set("soar", e.target.value)}>
                {SOARS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="ni-analyst">Assign analyst (optional)</label>
            <input
              id="ni-analyst"
              value={form.assigned_analyst}
              onChange={(e) => set("assigned_analyst", e.target.value)}
              placeholder="e.g. A. Rao"
            />
          </div>
          <div style={{ display: "flex", gap: "0.6rem", justifyContent: "flex-end" }}>
            <button type="button" className="btn secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={submitting}>
              {submitting ? "Creating…" : "Create Incident"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
