function fmt(value, digits = 1) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(digits);
}

function Delta({ deltaPct, higherIsBetter }) {
  if (deltaPct === null || deltaPct === undefined) {
    return <span className="delta flat">— vs last wk</span>;
  }
  const isUp = deltaPct > 0;
  const isGood = isUp ? higherIsBetter : !higherIsBetter;
  const arrow = isUp ? "▲" : deltaPct < 0 ? "▼" : "▬";
  const cls = deltaPct === 0 ? "flat" : isGood ? "good" : "bad";
  return (
    <span className={`delta ${cls}`}>
      {arrow} {Math.abs(deltaPct).toFixed(1)}% vs last wk
    </span>
  );
}

function Card({ label, value, unit, deltaPct, higherIsBetter }) {
  return (
    <div className="kpi-card">
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit ? <span style={{ fontSize: "0.9rem", color: "var(--text-soft)" }}> {unit}</span> : null}
      </div>
      <Delta deltaPct={deltaPct} higherIsBetter={higherIsBetter} />
    </div>
  );
}

export default function KPICards({ kpis }) {
  if (!kpis) return null;

  return (
    <>
      <div className="kpi-section">
        <h2>Volume</h2>
        <div className="kpi-grid">
          <Card label="Alerts" value={fmt(kpis.alerts.value, 0)} deltaPct={kpis.alerts.delta_pct} higherIsBetter={false} />
          <Card
            label="Critical Alerts"
            value={fmt(kpis.critical_alerts.value, 0)}
            deltaPct={kpis.critical_alerts.delta_pct}
            higherIsBetter={false}
          />
          <Card
            label="Incidents"
            value={fmt(kpis.incidents.value, 0)}
            deltaPct={kpis.incidents.delta_pct}
            higherIsBetter={false}
          />
        </div>
      </div>

      <div className="kpi-section">
        <h2>Responsiveness</h2>
        <div className="kpi-grid">
          <Card
            label="Avg MTTD"
            value={fmt(kpis.avg_mttd_minutes.value)}
            unit="min"
            deltaPct={kpis.avg_mttd_minutes.delta_pct}
            higherIsBetter={false}
          />
          <Card
            label="Avg MTTR"
            value={fmt(kpis.avg_mttr_hours.value)}
            unit="hrs"
            deltaPct={kpis.avg_mttr_hours.delta_pct}
            higherIsBetter={false}
          />
          <Card
            label="P1 Avg Response"
            value={fmt(kpis.p1_avg_response_minutes.value)}
            unit="min"
            deltaPct={kpis.p1_avg_response_minutes.delta_pct}
            higherIsBetter={false}
          />
          <Card
            label="P2 Avg Response"
            value={fmt(kpis.p2_avg_response_minutes.value)}
            unit="min"
            deltaPct={kpis.p2_avg_response_minutes.delta_pct}
            higherIsBetter={false}
          />
          <Card
            label="P3 Avg Response"
            value={fmt(kpis.p3_avg_response_minutes.value)}
            unit="min"
            deltaPct={kpis.p3_avg_response_minutes.delta_pct}
            higherIsBetter={false}
          />
        </div>
      </div>

      <div className="kpi-section">
        <h2>Quality</h2>
        <div className="kpi-grid">
          <Card
            label="SLA Compliance"
            value={fmt(kpis.sla_compliance_pct.value)}
            unit="%"
            deltaPct={kpis.sla_compliance_pct.delta_pct}
            higherIsBetter={true}
          />
          <Card
            label="SLA Breaches"
            value={fmt(kpis.sla_breaches.value, 0)}
            deltaPct={kpis.sla_breaches.delta_pct}
            higherIsBetter={false}
          />
          <Card
            label="False-Positive Rate"
            value={fmt(kpis.false_positive_rate_pct.value)}
            unit="%"
            deltaPct={kpis.false_positive_rate_pct.delta_pct}
            higherIsBetter={false}
          />
        </div>
      </div>
    </>
  );
}
