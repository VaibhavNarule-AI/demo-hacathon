import { useEffect, useState } from "react";
import GlobalFilterBar from "../components/GlobalFilterBar";
import IncidentTable from "../components/IncidentTable";
import KPICards from "../components/KPICards";
import Layout from "../components/Layout";
import { MttrSlaTrendChart, VolumeTrendChart } from "../components/TrendChart";
import api from "../services/api";

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function defaultFilters(fixedCustomer) {
  const to = new Date();
  const from = new Date(to.getTime() - 7 * 24 * 60 * 60 * 1000);
  return {
    customer: fixedCustomer || "",
    siem: "",
    soar: "",
    tier: "",
    from: isoDate(from),
    to: isoDate(to),
  };
}

function toQuery(filters) {
  const params = {};
  if (filters.customer) params.customer = filters.customer;
  if (filters.siem) params.siem = filters.siem;
  if (filters.soar) params.soar = filters.soar;
  if (filters.tier) params.tier = filters.tier;
  if (filters.from) params.from = `${filters.from}T00:00:00`;
  if (filters.to) params.to = `${filters.to}T23:59:59`;
  return params;
}

const SLA_BREACH_HOURS = 4;
const AT_RISK_THRESHOLD_HOURS = 3; // warn before the 4h P1 breach threshold hits

function atRiskIncidents(incidents) {
  const now = Date.now();
  return incidents.filter((inc) => {
    if (inc.severity !== "Critical" || !inc.opened_time || inc.closed_time) return false;
    const openedHoursAgo = (now - new Date(inc.opened_time).getTime()) / 3_600_000;
    return openedHoursAgo >= AT_RISK_THRESHOLD_HOURS && openedHoursAgo < SLA_BREACH_HOURS;
  });
}

function AtRiskBanner({ incidents }) {
  const atRisk = atRiskIncidents(incidents);
  if (atRisk.length === 0) return null;
  return (
    <div className="at-risk-banner">
      <strong>{atRisk.length} P1 incident{atRisk.length > 1 ? "s" : ""}</strong> open{" "}
      {AT_RISK_THRESHOLD_HOURS}+ hours — will breach SLA at {SLA_BREACH_HOURS}h if not closed soon:{" "}
      {atRisk.map((i) => i.ticket_number).join(", ")}
    </div>
  );
}

export default function Dashboard() {
  const fixedCustomer = localStorage.getItem("customer_id") || "";
  const [filters, setFilters] = useState(defaultFilters(fixedCustomer));
  const [customers, setCustomers] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [volumeTrend, setVolumeTrend] = useState([]);
  const [mttrTrend, setMttrTrend] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [latencyMs, setLatencyMs] = useState(null);

  useEffect(() => {
    api.get("/customers").then((res) => setCustomers(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const started = performance.now();
    const params = toQuery(filters);

    Promise.all([
      api.get("/analytics/kpis", { params }),
      api.get("/analytics/trends", { params: { ...params, metric: "volume" } }),
      api.get("/analytics/trends", { params: { ...params, metric: "mttr" } }),
      api.get("/incidents", { params }),
    ])
      .then(([kpiRes, volRes, mttrRes, incRes]) => {
        if (cancelled) return;
        setKpis(kpiRes.data);
        setVolumeTrend(volRes.data);
        setMttrTrend(mttrRes.data);
        setIncidents(incRes.data);
        setLatencyMs(Math.round(performance.now() - started));
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || "Failed to load dashboard data.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters]);

  return (
    <Layout title="SOC Executive Dashboard" latencyMs={latencyMs}>
      <GlobalFilterBar
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters(defaultFilters(fixedCustomer))}
        customers={customers}
        fixedCustomer={fixedCustomer}
      />

      {error && <div className="error-state">{error}</div>}
      {loading && !kpis && <div className="loading-state">Loading dashboard…</div>}

      <AtRiskBanner incidents={incidents} />

      {kpis && <KPICards kpis={kpis} />}

      <div className="chart-grid">
        <VolumeTrendChart data={volumeTrend} />
        <MttrSlaTrendChart data={mttrTrend} />
      </div>

      <IncidentTable incidents={incidents} loading={loading} />
    </Layout>
  );
}
