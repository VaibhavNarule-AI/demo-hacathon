import { useState } from "react";
import api from "../services/api";

export default function CloseIncidentModal({ ticket, onClose, onClosed }) {
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const res = await api.post(`/incidents/${ticket.incident_id}/close`, { resolution_notes: notes });
      onClosed(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not close incident.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Close {ticket.ticket_number}</h3>
        <p style={{ color: "var(--text-soft)", fontSize: "0.88rem" }}>
          {ticket.customer} · {ticket.severity} · {ticket.breaches_in}
        </p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
          <div>
            <label htmlFor="notes">Resolution notes (optional)</label>
            <input
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="What was done to resolve this"
              autoFocus
            />
          </div>
          <div style={{ display: "flex", gap: "0.6rem", justifyContent: "flex-end" }}>
            <button type="button" className="btn secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn" disabled={submitting}>
              {submitting ? "Closing…" : "Close / Resolve Now"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
