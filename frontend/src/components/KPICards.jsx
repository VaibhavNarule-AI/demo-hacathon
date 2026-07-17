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

function Sparkline({ data }) {
  const values = (data || []).filter((v) => v !== null && v !== undefined);
  if (values.length < 2) return null;
  const w = 68;
  const h = 22;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="sparkline" aria-hidden="true">
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Card({ label, value, unit, deltaPct, higherIsBetter, info, sparkline }) {
  return (
    <div className="kpi-card">
      <div className="kpi-card-top">
        <div className="label">
          {label} {info && <span className="info-icon" title={info}>ⓘ</span>}
        </div>
        <Sparkline data={sparkline} />
      </div>
      <div className="value">
        {value}
        {unit ? <span style={{ fontSize: "0.9rem", color: "var(--text-soft)" }}> {unit}</span> : null}
      </div>
      <Delta deltaPct={deltaPct} higherIsBetter={higherIsBetter} />
    </div>
  );
}

export function KPICardsSkeleton() {
  return (
    <div className="kpi-grid" style={{ marginBottom: "1.6rem" }}>
      {Array.from({ length: 9 }).map((_, i) => (
        <div key={i} className="skeleton-block" style={{ height: 100 }} />
      ))}
    </div>
  );
}

export default function KPICards({ kpis, volumeTrend, mttrTrend }) {
  if (!kpis) return null;

  const alertsSpark = (volumeTrend || []).map((p) => p.values.alerts);
  const incidentsSpark = (volumeTrend || []).map((p) => p.values.incidents);
  const mttrSpark = (mttrTrend || []).map((p) => p.values.avg_mttr_hours);
  const slaSpark = (mttrTrend || []).map((p) => p.values.sla_compliance_pct);

  return (
    <>
      <div className="kpi-section">
        <h2>Volume</h2>
        <div className="kpi-grid">
          <Card
            label="Alerts"
            value={fmt(kpis.alerts.value, 0)}
            deltaPct={kpis.alerts.delta_pct}
            higherIsBetter={false}
            info="COUNT(*) WHERE created_time in range — every row that reaches the platform, before any funnel filtering."
            sparkline={alertsSpark}
          />
          <Card
            label="Critical Alerts"
            value={fmt(kpis.critical_alerts.value, 0)}
            deltaPct={kpis.critical_alerts.delta_pct}
            higherIsBetter={false}
            info="Alerts WHERE severity = 'Critical'."
          />
          <Card
            label="Incidents"
            value={fmt(kpis.incidents.value, 0)}
            deltaPct={kpis.incidents.delta_pct}
            higherIsBetter={false}
            info="Alerts WHERE opened_time IS NOT NULL — the alert→incident funnel."
            sparkline={incidentsSpark}
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
            info="avg(created_time − event_time), minutes — detection latency."
          />
          <Card
            label="Avg MTTR"
            value={fmt(kpis.avg_mttr_hours.value)}
            unit="hrs"
            deltaPct={kpis.avg_mttr_hours.delta_pct}
            higherIsBetter={false}
            info="avg(closed_time − opened_time) for closed incidents only, hours."
            sparkline={mttrSpark}
          />
          <Card
            label="P1 Avg Response"
            value={fmt(kpis.p1_avg_response_minutes.value)}
            unit="min"
            deltaPct={kpis.p1_avg_response_minutes.delta_pct}
            higherIsBetter={false}
            info="avg(first_response_time − opened_time) for Critical incidents."
          />
          <Card
            label="P2 Avg Response"
            value={fmt(kpis.p2_avg_response_minutes.value)}
            unit="min"
            deltaPct={kpis.p2_avg_response_minutes.delta_pct}
            higherIsBetter={false}
            info="avg(first_response_time − opened_time) for Major incidents."
          />
          <Card
            label="P3 Avg Response"
            value={fmt(kpis.p3_avg_response_minutes.value)}
            unit="min"
            deltaPct={kpis.p3_avg_response_minutes.delta_pct}
            higherIsBetter={false}
            info="avg(first_response_time − opened_time) for Minor incidents. Informational has no SLA/P-bucket."
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
            info="Matched / (Matched + Breached) × 100 — never-opened incidents excluded from the denominator entirely."
            sparkline={slaSpark}
          />
          <Card
            label="SLA Breaches"
            value={fmt(kpis.sla_breaches.value, 0)}
            deltaPct={kpis.sla_breaches.delta_pct}
            higherIsBetter={false}
            info="COUNT(*) WHERE sla_result = 'Breached'."
          />
          <Card
            label="False-Positive Rate"
            value={fmt(kpis.false_positive_rate_pct.value)}
            unit="%"
            deltaPct={kpis.false_positive_rate_pct.delta_pct}
            higherIsBetter={false}
            info="false_positive count / Alerts × 100."
          />
        </div>
      </div>
    </>
  );
}
