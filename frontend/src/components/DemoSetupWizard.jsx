import { useState } from "react";
import api from "../services/api";

const STEPS = ["Register Partner", "Create Customer", "Configure SLA", "Create Ticket"];

export default function DemoSetupWizard({ onClose, onComplete }) {
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [partner, setPartner] = useState({
    partner_name: "Demo Partner",
    partner_id: "demo-partner",
    contact_email: "demo@test.com",
  });
  const [customer, setCustomer] = useState({
    customer_name: "Demo Customer",
    customer_id: "demo-customer-1",
    service_tier: "Gold",
    siem: "QRADAR",
    soar: "XSOAR",
  });
  const [sla, setSla] = useState({ Critical: 5, Major: 10, Minor: 30 });
  const [ticket, setTicket] = useState({
    severity: "Critical",
    summary: "Demo Critical - Will blink in 5 min",
    category: "Malware",
  });

  async function next() {
    setError("");
    setSubmitting(true);
    try {
      if (step === 0) {
        await api.post("/partners/register", partner);
      } else if (step === 1) {
        await api.post(`/partners/${partner.partner_id}/customers/create`, customer);
      } else if (step === 2) {
        for (const sev of ["Critical", "Major", "Minor"]) {
          await api.post("/sla-config", {
            partner_id: partner.partner_id,
            customer_id: customer.customer_id,
            severity: sev,
            sla_minutes: Number(sla[sev]),
          });
        }
      } else if (step === 3) {
        await api.post("/incidents/create", {
          customer: customer.customer_id,
          severity: ticket.severity,
          category: ticket.category,
          summary: ticket.summary,
          siem: customer.siem,
          soar: customer.soar,
        });
        onComplete(partner.partner_id, customer.customer_id);
        return;
      }
      setStep((s) => s + 1);
    } catch (err) {
      setError(err.response?.data?.detail || "Step failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Demo Setup — Step {step + 1} of {STEPS.length}: {STEPS[step]}</h3>
        {error && <div className="error">{error}</div>}

        {step === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
            <div>
              <label htmlFor="dw-pname">Partner Name</label>
              <input id="dw-pname" value={partner.partner_name} onChange={(e) => setPartner((p) => ({ ...p, partner_name: e.target.value }))} />
            </div>
            <div>
              <label htmlFor="dw-pid">Partner ID</label>
              <input id="dw-pid" value={partner.partner_id} onChange={(e) => setPartner((p) => ({ ...p, partner_id: e.target.value }))} />
            </div>
            <div>
              <label htmlFor="dw-pemail">Contact Email</label>
              <input id="dw-pemail" value={partner.contact_email} onChange={(e) => setPartner((p) => ({ ...p, contact_email: e.target.value }))} />
            </div>
          </div>
        )}

        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
            <div>
              <label htmlFor="dw-cname">Customer Name</label>
              <input id="dw-cname" value={customer.customer_name} onChange={(e) => setCustomer((c) => ({ ...c, customer_name: e.target.value }))} />
            </div>
            <div>
              <label htmlFor="dw-cid">Customer ID</label>
              <input id="dw-cid" value={customer.customer_id} onChange={(e) => setCustomer((c) => ({ ...c, customer_id: e.target.value }))} />
            </div>
            <div>
              <label htmlFor="dw-tier">Tier</label>
              <select id="dw-tier" value={customer.service_tier} onChange={(e) => setCustomer((c) => ({ ...c, service_tier: e.target.value }))}>
                <option>Gold</option>
                <option>Silver</option>
                <option>Bronze</option>
              </select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
            <p style={{ color: "var(--text-soft)", fontSize: "0.85rem" }}>
              Set a short SLA on Critical so the demo ticket blinks immediately.
            </p>
            {["Critical", "Major", "Minor"].map((sev) => (
              <div key={sev}>
                <label htmlFor={`dw-sla-${sev}`}>{sev} SLA (minutes)</label>
                <input
                  id={`dw-sla-${sev}`}
                  type="number"
                  min="1"
                  value={sla[sev]}
                  onChange={(e) => setSla((s) => ({ ...s, [sev]: e.target.value }))}
                />
              </div>
            ))}
          </div>
        )}

        {step === 3 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
            <p style={{ color: "var(--text-soft)", fontSize: "0.88rem" }}>
              Creates a {ticket.severity} ticket for {customer.customer_name} — with the {sla[ticket.severity]} min SLA
              just configured, it should show as blinking in the Early Warning table immediately.
            </p>
            <div>
              <label htmlFor="dw-summary">Summary</label>
              <input id="dw-summary" value={ticket.summary} onChange={(e) => setTicket((t) => ({ ...t, summary: e.target.value }))} />
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: "0.6rem", justifyContent: "flex-end", marginTop: "1.2rem" }}>
          <button className="btn secondary" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={next} disabled={submitting}>
            {submitting ? "Working…" : step === STEPS.length - 1 ? "Create Ticket & Finish" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
