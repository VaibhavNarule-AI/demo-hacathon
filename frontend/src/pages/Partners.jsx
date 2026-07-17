import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../services/api";

const SEVERITIES = ["Critical", "Major", "Minor"];
const DEFAULT_SLA = { Critical: 240, Major: 480, Minor: 1440 };
const TIERS = ["Gold", "Silver", "Bronze"];
const SIEMS = ["QRADAR", "XSIAM"];
const SOARS = ["XSOAR", "Resilient"];

function slugify(name) {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

export default function Partners() {
  const role = localStorage.getItem("role");
  const ownPartnerId = localStorage.getItem("partner_id") || "";
  const [tab, setTab] = useState("register");
  const [partners, setPartners] = useState([]);
  const [status, setStatus] = useState("");

  // Register Partner tab state
  const [partnerName, setPartnerName] = useState("");
  const [partnerId, setPartnerId] = useState("");
  const [contactEmail, setContactEmail] = useState("");

  // Configure SLA tab state
  const [selectedPartner, setSelectedPartner] = useState(ownPartnerId || "");
  const [customers, setCustomers] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [slaDraft, setSlaDraft] = useState({ Critical: "", Major: "", Minor: "" });
  const [slaCustomer, setSlaCustomer] = useState("");

  function loadPartners() {
    if (role === "super_admin") {
      api.get("/partners/list").then((res) => setPartners(res.data)).catch(() => {});
    }
  }

  useEffect(loadPartners, [role]);

  useEffect(() => {
    if (!selectedPartner) return;
    api.get(`/partners/${selectedPartner}/customers`).then((res) => setCustomers(res.data)).catch(() => setCustomers([]));
    api.get("/sla-config", { params: { partner: selectedPartner } }).then((res) => setConfigs(res.data)).catch(() => setConfigs([]));
  }, [selectedPartner]);

  async function handleRegister(e) {
    e.preventDefault();
    setStatus("Registering…");
    try {
      const res = await api.post("/partners/register", {
        partner_name: partnerName,
        partner_id: partnerId || slugify(partnerName),
        contact_email: contactEmail,
      });
      setStatus(`Partner ${res.data.partner_id} created`);
      setPartnerName("");
      setPartnerId("");
      setContactEmail("");
      loadPartners();
    } catch (err) {
      setStatus(err.response?.data?.detail || "Could not register partner.");
    }
  }

  async function saveSla(severity) {
    const minutes = Number(slaDraft[severity]);
    if (!minutes || minutes <= 0) return;
    try {
      await api.post("/sla-config", {
        partner_id: selectedPartner,
        customer_id: slaCustomer || null,
        severity,
        sla_minutes: minutes,
      });
      const scope = slaCustomer ? `${selectedPartner} ${slaCustomer}` : selectedPartner;
      setStatus(`SLA for ${severity} set to ${minutes} min for ${scope} — for demo blinking`);
      const res = await api.get("/sla-config", { params: { partner: selectedPartner } });
      setConfigs(res.data);
    } catch (err) {
      setStatus(err.response?.data?.detail || "Could not save SLA config.");
    }
  }

  return (
    <Layout latencyMs={null}>
      <div className="table-card" style={{ marginBottom: "1.2rem" }}>
        <div style={{ display: "flex", gap: "0.5rem", padding: "1rem 1.2rem 0" }}>
          {role === "super_admin" && (
            <button className={`btn ${tab === "register" ? "" : "secondary"}`} onClick={() => setTab("register")}>
              Register Partner
            </button>
          )}
          <button className={`btn ${tab === "sla" ? "" : "secondary"}`} onClick={() => setTab("sla")}>
            Configure SLA
          </button>
        </div>

        {status && <p style={{ padding: "0 1.2rem", color: "var(--text-soft)" }}>{status}</p>}

        {tab === "register" && role === "super_admin" && (
          <form onSubmit={handleRegister} style={{ padding: "1rem 1.2rem 1.4rem", display: "flex", flexDirection: "column", gap: "0.9rem", maxWidth: 420 }}>
            <div>
              <label htmlFor="p-name">Partner Name</label>
              <input id="p-name" value={partnerName} onChange={(e) => { setPartnerName(e.target.value); if (!partnerId) setPartnerId(slugify(e.target.value)); }} required />
            </div>
            <div>
              <label htmlFor="p-id">Partner ID (slug)</label>
              <input id="p-id" value={partnerId} onChange={(e) => setPartnerId(e.target.value)} required />
            </div>
            <div>
              <label htmlFor="p-email">Contact Email</label>
              <input id="p-email" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
            </div>
            <button className="btn" type="submit">Create</button>
          </form>
        )}

        {tab === "sla" && (
          <div style={{ padding: "1rem 1.2rem 1.4rem" }}>
            <div className="field" style={{ marginBottom: "1rem" }}>
              <label>Partner</label>
              {role === "super_admin" ? (
                <select value={selectedPartner} onChange={(e) => setSelectedPartner(e.target.value)}>
                  <option value="">Select a partner…</option>
                  {partners.map((p) => (
                    <option key={p.partner_id} value={p.partner_id}>{p.partner_name} ({p.partner_id})</option>
                  ))}
                </select>
              ) : (
                <input value={selectedPartner} disabled />
              )}
            </div>

            {selectedPartner && (
              <>
                <div className="field" style={{ marginBottom: "1rem", maxWidth: 260 }}>
                  <label title="Leave blank to set a partner-wide default">Customer override (optional)</label>
                  <select value={slaCustomer} onChange={(e) => setSlaCustomer(e.target.value)}>
                    <option value="">Partner-wide default</option>
                    {customers.map((c) => (
                      <option key={c.customer_id} value={c.customer_id}>{c.customer_name}</option>
                    ))}
                  </select>
                </div>

                <table className="incident-table">
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>Default SLA</th>
                      <th>Custom SLA (min)</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {SEVERITIES.map((sev) => (
                      <tr key={sev}>
                        <td><span className={`badge ${sev}`}>{sev}</span></td>
                        <td className="mono">{DEFAULT_SLA[sev]} min</td>
                        <td>
                          <input
                            type="number"
                            min="1"
                            style={{ width: 90 }}
                            value={slaDraft[sev]}
                            onChange={(e) => setSlaDraft((d) => ({ ...d, [sev]: e.target.value }))}
                            placeholder="mins"
                          />
                        </td>
                        <td>
                          <button className="btn secondary" onClick={() => saveSla(sev)}>Save</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <h3 style={{ marginTop: "1.4rem", fontSize: "0.85rem", color: "var(--text-soft)" }}>Current SLA configs</h3>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.5rem" }}>
                  {configs.length === 0 && <span style={{ color: "var(--text-soft)", fontSize: "0.85rem" }}>None set — using global defaults.</span>}
                  {configs.map((c) => (
                    <span key={c.id} className="chip">
                      {c.severity}: {c.sla_minutes}min {c.customer_id ? `(${c.customer_id})` : "(partner default)"}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
