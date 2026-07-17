import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ChartCard from "../components/ChartCard";
import GlobalFilterBar from "../components/GlobalFilterBar";
import KPICards, { KPICardsSkeleton } from "../components/KPICards";
import { useApp } from "../context/AppContext";
import api from "../services/api";
import { errorMessage } from "../utils/errors";

const SEVERITY_COLORS = { Critical: "#f87171", Major: "#fbbf24", Minor: "#3aa0ff", Informational: "#34d399" };

function toQuery(filters) {
  const params = {};
  if (filters.customers.length) params.customer = filters.customers.join(",");
  if (filters.siem.length) params.siem = filters.siem.join(",");
  if (filters.soar.length) params.soar = filters.soar.join(",");
  if (filters.tier) params.tier = filters.tier;
  if (filters.from) params.from = `${filters.from}T00:00:00`;
  if (filters.to) params.to = `${filters.to}T23:59:59`;
  return params;
}

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function last30DaysParams(filters) {
  const to = new Date();
  const from = new Date(to.getTime() - 30 * 24 * 60 * 60 * 1000);
  return {
    ...(filters.customers.length && { customer: filters.customers.join(",") }),
    ...(filters.siem.length && { siem: filters.siem.join(",") }),
    ...(filters.soar.length && { soar: filters.soar.join(",") }),
    ...(filters.tier && { tier: filters.tier }),
    from: `${isoDate(from)}T00:00:00`,
    to: `${isoDate(to)}T23:59:59`,
  };
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { filters, setFilters, resetFilters, fixedCustomer, customers, refreshKey, breachRisk } = useApp();
  const [kpis, setKpis] = useState(null);
  const [dailyTrend, setDailyTrend] = useState([]);
  const [mttrTrend, setMttrTrend] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [topPriority, setTopPriority] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const params = toQuery(filters);

    Promise.all([
      api.get("/analytics/kpis", { params }),
      api.get("/analytics/trends", { params: { ...last30DaysParams(filters), metric: "volume", bucket: "daily" } }),
      api.get("/analytics/trends", { params: { ...params, metric: "mttr" } }),
      api.get("/incidents/drill-down", { params }),
      api.get("/analytics/priority-ranking", { params: { limit: 1 } }),
    ])
      .then(([kpiRes, trendRes, mttrRes, incRes, priorityRes]) => {
        if (cancelled) return;
        setKpis(kpiRes.data);
        setDailyTrend(trendRes.data);
        setMttrTrend(mttrRes.data);
        setIncidents(incRes.data);
        setTopPriority(priorityRes.data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, "Failed to load dashboard."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters, refreshKey]);

  const resultLabel = kpis
    ? `Showing ${Math.round(kpis.alerts.value)} alerts from ${filters.customers.length || customers.length} customer${
        (filters.customers.length || customers.length) === 1 ? "" : "s"
      }`
    : "";

  const severityCounts = {};
  incidents.forEach((i) => {
    severityCounts[i.severity] = (severityCounts[i.severity] || 0) + 1;
  });
  const severityData = Object.entries(severityCounts).map(([severity, value]) => ({
    severity,
    value,
    color: SEVERITY_COLORS[severity],
  }));

  const customerCounts = {};
  incidents.forEach((i) => {
    customerCounts[i.customer] = (customerCounts[i.customer] || 0) + 1;
  });
  const topCustomers = Object.entries(customerCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([customer, count]) => ({ customer, count }));

  const siemSoarMap = {};
  incidents.forEach((i) => {
    siemSoarMap[i.siem] = siemSoarMap[i.siem] || { siem: i.siem, XSOAR: 0, Resilient: 0 };
    siemSoarMap[i.siem][i.soar] = (siemSoarMap[i.siem][i.soar] || 0) + 1;
  });
  const siemSoarData = Object.values(siemSoarMap);

  const highRisk = breachRisk.filter((r) => r.risk === "HIGH" || r.risk === "BLINKING");

  function goIncidents(extraParams) {
    const qs = new URLSearchParams({ ...toQuery(filters), ...extraParams }).toString();
    navigate(`/incidents?${qs}`);
  }

  return (
    <>
      <GlobalFilterBar
        filters={filters}
        onChange={setFilters}
        onReset={resetFilters}
        customers={customers}
        fixedCustomer={fixedCustomer}
        resultLabel={resultLabel}
      />

      {error && <div className="error-state">{error}</div>}

      {loading && !kpis ? (
        <KPICardsSkeleton />
      ) : (
        kpis && <KPICards kpis={kpis} volumeTrend={dailyTrend} mttrTrend={mttrTrend} />
      )}

      <div className="chart-grid">
        <ChartCard
          title="Alerts Trend (last 30 days)"
          subtitle="Click a day to drill into that date in Incidents"
          type="line"
          data={dailyTrend.map((p) => ({ day: p.week_start.slice(5), alerts: p.values.alerts, incidents: p.values.incidents }))}
          xKey="day"
          series={[
            { key: "alerts", label: "Alerts", color: "#3aa0ff" },
            { key: "incidents", label: "Incidents", color: "#34d399" },
          ]}
          onSliceClick={(point) => goIncidents({ from: `${point.day}T00:00:00`, to: `${point.day}T23:59:59` })}
        />
        <ChartCard
          title="Severity Breakdown"
          subtitle="Click a slice to filter Incidents by severity"
          type="donut"
          data={severityData}
          onSliceClick={(slice) => goIncidents({ severity: slice.severity })}
        />
      </div>

      <div className="chart-grid">
        <ChartCard
          title="Top Customers by Volume"
          subtitle="Click a bar to filter Incidents by customer"
          type="bar"
          data={topCustomers}
          xKey="customer"
          series={[{ key: "count", label: "Incidents", color: "#3aa0ff" }]}
          onSliceClick={(row) => goIncidents({ customer: row.customer })}
        />
        <ChartCard
          title="SIEM vs SOAR"
          subtitle="Click a segment to filter Incidents"
          type="stacked-bar"
          data={siemSoarData}
          xKey="siem"
          series={[
            { key: "XSOAR", label: "XSOAR", color: "#3aa0ff" },
            { key: "Resilient", label: "Resilient", color: "#34d399" },
          ]}
          onSliceClick={(row, i, key) => goIncidents({ siem: row.siem, soar: key })}
        />
      </div>

      <div className="dashboard-summary-row">
        <div className="table-card summary-card">
          <div className="summary-header">
            <h3>SLA Breach Predictor</h3>
            <a href="/breach-predictor" className="btn-link">View All →</a>
          </div>
          {highRisk.length > 0 ? (
            <div className="breach-banner" style={{ margin: 0 }}>
              ⚠️ {highRisk.length} incident{highRisk.length > 1 ? "s" : ""} at risk — Act now
            </div>
          ) : (
            <div className="empty-state" style={{ padding: "1rem 0" }}>All clear — nothing at risk right now.</div>
          )}
        </div>

        <div className="table-card summary-card">
          <div className="summary-header">
            <h3>Smart Priority — Top Incident</h3>
            <a href="/incidents" className="btn-link">View All →</a>
          </div>
          {topPriority.length > 0 ? (
            <div className="priority-summary">
              <div className="priority-summary-top">
                <span className="mono priority-summary-ticket">{topPriority[0].ticket_number}</span>
                <span className={`priority-badge priority-${topPriority[0].priority_label.split(" ")[0].toLowerCase()}`}>
                  {topPriority[0].priority_score} / 100
                </span>
              </div>
              <p className="priority-summary-reason">{topPriority[0].reasons.join(" · ")}</p>
              <p className="priority-summary-action">
                Recommended Action: <strong>{topPriority[0].recommended_action}</strong>
              </p>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: "1rem 0" }}>No open incidents to prioritize right now.</div>
          )}
        </div>
      </div>
    </>
  );
}
