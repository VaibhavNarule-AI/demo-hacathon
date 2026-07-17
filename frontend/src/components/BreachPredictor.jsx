const RISK_ORDER = { HIGH: 0, MEDIUM: 1, LOW: 2, BREACHED: 3 };

function ProgressBar({ pct, risk }) {
  const width = Math.min(100, pct);
  return (
    <div className="risk-bar-track">
      <div className={`risk-bar-fill risk-${risk}`} style={{ width: `${width}%` }} />
    </div>
  );
}

export default function BreachPredictor({ risk, loading, onFocusCustomer, onRequestClose }) {
  if (loading) {
    return <div className="skeleton-block" style={{ height: 60, marginBottom: "1.4rem" }} />;
  }

  const highRisk = risk.filter((r) => r.risk === "HIGH");
  const actionable = risk
    .filter((r) => r.risk !== "LOW")
    .sort((a, b) => RISK_ORDER[a.risk] - RISK_ORDER[b.risk] || b.pct - a.pct)
    .slice(0, 12);

  return (
    <div className="breach-predictor">
      {highRisk.length > 0 && (
        <div className="breach-banner">
          ⚠️ {highRisk.length} incident{highRisk.length > 1 ? "s" : ""} at risk of SLA breach — Act now
        </div>
      )}

      <div className="table-card" style={{ marginBottom: "1.4rem" }}>
        <h3>Early Warning System — SLA Breach Predictor</h3>
        {actionable.length === 0 ? (
          <div className="empty-state">No incidents currently at risk. All open tickets are well within SLA.</div>
        ) : (
          <table className="incident-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Customer</th>
                <th>Severity</th>
                <th>Progress</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {actionable.map((r) => (
                <tr key={r.incident_id}>
                  <td className="mono" onClick={() => onFocusCustomer(r.customer)}>
                    {r.blinking_critical ? (
                      <span className="ticket-blink">{r.ticket_number}</span>
                    ) : (
                      r.ticket_number
                    )}
                  </td>
                  <td onClick={() => onFocusCustomer(r.customer)}>{r.customer}</td>
                  <td onClick={() => onFocusCustomer(r.customer)}>
                    <span className={`badge ${r.severity}`}>{r.severity}</span>
                  </td>
                  <td style={{ minWidth: 160 }} onClick={() => onFocusCustomer(r.customer)}>
                    <ProgressBar pct={r.pct} risk={r.risk} />
                  </td>
                  <td onClick={() => onFocusCustomer(r.customer)}>
                    <span className={`risk-label risk-${r.risk}`}>
                      {r.risk === "BREACHED" ? "Breached" : r.breaches_in}
                    </span>
                  </td>
                  <td>
                    <button className="btn secondary" onClick={() => onRequestClose(r)}>
                      Close / Resolve Now
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
