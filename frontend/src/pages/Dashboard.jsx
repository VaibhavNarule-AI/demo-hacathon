import { useEffect, useRef, useState } from "react";
import BreachPredictor from "../components/BreachPredictor";
import CloseIncidentModal from "../components/CloseIncidentModal";
import CommandCenter from "../components/CommandCenter";
import Confetti from "../components/Confetti";
import CustomerHealth from "../components/CustomerHealth";
import DemoSetupWizard from "../components/DemoSetupWizard";
import GlobalFilterBar from "../components/GlobalFilterBar";
import IncidentTable from "../components/IncidentTable";
import KPICards, { KPICardsSkeleton } from "../components/KPICards";
import Layout from "../components/Layout";
import NewIncidentModal from "../components/NewIncidentModal";
import Toast from "../components/Toast";
import { MttrSlaTrendChart, VolumeTrendChart } from "../components/TrendChart";
import WarRoomBanner from "../components/WarRoomBanner";
import api from "../services/api";

const REFRESH_MS = 30_000;
const BREACH_RISK_REFRESH_MS = 30_000;

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function defaultFilters(fixedCustomer) {
  const to = new Date();
  const from = new Date(to.getTime() - 90 * 24 * 60 * 60 * 1000);
  return {
    customers: fixedCustomer ? [fixedCustomer] : [],
    siem: [],
    soar: [],
    tier: "",
    rangePreset: "90d",
    from: isoDate(from),
    to: isoDate(to),
  };
}

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
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [showNewIncident, setShowNewIncident] = useState(false);
  const [showCommandCenter, setShowCommandCenter] = useState(false);
  const [showDemoSetup, setShowDemoSetup] = useState(false);
  const [toasts, setToasts] = useState([]);
  const toastId = useRef(0);

  const [breachRisk, setBreachRisk] = useState([]);
  const [breachRiskLoading, setBreachRiskLoading] = useState(true);
  const [breachRiskFetchedAt, setBreachRiskFetchedAt] = useState(Date.now());
  const [closingTicket, setClosingTicket] = useState(null);
  const [confettiTrigger, setConfettiTrigger] = useState(0);

  function pushToast(message, kind = "info") {
    const id = ++toastId.current;
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }

  function loadCustomers() {
    api.get("/customers").then((res) => setCustomers(res.data)).catch(() => {});
  }

  useEffect(loadCustomers, []);

  function loadBreachRisk() {
    api.get("/analytics/breach-risk").then((res) => {
      setBreachRisk(res.data);
      setBreachRiskFetchedAt(Date.now());
      setBreachRiskLoading(false);
    }).catch(() => setBreachRiskLoading(false));
  }

  useEffect(() => {
    loadBreachRisk();
    const id = setInterval(loadBreachRisk, BREACH_RISK_REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;

    function load() {
      setError("");
      const started = performance.now();
      const params = toQuery(filters);

      return Promise.all([
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
          setLastUpdatedAt(Date.now());
        })
        .catch((err) => {
          if (!cancelled) setError(err.response?.data?.detail || "Failed to load dashboard data.");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }

    setLoading(true);
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [filters]);

  function refreshAll() {
    setFilters((f) => ({ ...f }));
    loadBreachRisk();
  }

  function focusCustomer(customerId) {
    if (fixedCustomer) return;
    setFilters((f) => ({ ...f, customers: [customerId] }));
  }

  function handleIncidentCreated(incident) {
    setShowNewIncident(false);
    pushToast(`Incident ${incident.ticket_number} created`, "success");
    refreshAll();
  }

  function handleIncidentClosed(updated) {
    setClosingTicket(null);
    if (updated.sla_saved_message) {
      pushToast(`${updated.ticket_number} closed — ${updated.sla_saved_message}`, "success");
      setConfettiTrigger((t) => t + 1);
    } else {
      pushToast(`${updated.ticket_number} closed (SLA already breached)`, "error");
    }
    refreshAll();
  }

  function handleDemoSetupComplete(partnerId, customerId) {
    setShowDemoSetup(false);
    pushToast(`Demo ready — ${partnerId} / ${customerId} filtered in`, "success");
    loadCustomers();
    setFilters((f) => ({ ...f, customers: [customerId] }));
    loadBreachRisk();
  }

  const blinkingTickets = breachRisk
    .filter((r) => r.blinking_critical)
    .map((r) => ({ ...r, fetchedAt: breachRiskFetchedAt }));

  const resultLabel = kpis
    ? `Showing ${Math.round(kpis.alerts.value)} alerts from ${
        filters.customers.length || customers.length
      } customer${(filters.customers.length || customers.length) === 1 ? "" : "s"}`
    : "";

  if (showCommandCenter) {
    return <CommandCenter onExit={() => setShowCommandCenter(false)} />;
  }

  return (
    <>
      <WarRoomBanner blinkingTickets={blinkingTickets} onTakeAction={(ticket) => setClosingTicket(ticket)} />

      <Layout
        latencyMs={latencyMs}
        lastUpdatedAt={lastUpdatedAt}
        onNewIncident={() => setShowNewIncident(true)}
        onEnterCommandCenter={() => setShowCommandCenter(true)}
        onOpenDemoSetup={() => setShowDemoSetup(true)}
      >
        <GlobalFilterBar
          filters={filters}
          onChange={setFilters}
          onReset={() => setFilters(defaultFilters(fixedCustomer))}
          customers={customers}
          fixedCustomer={fixedCustomer}
          resultLabel={resultLabel}
        />

        {error && <div className="error-state">{error}</div>}

        <BreachPredictor
          risk={breachRisk}
          loading={breachRiskLoading}
          onFocusCustomer={focusCustomer}
          onRequestClose={(ticket) => setClosingTicket(ticket)}
        />

        {loading && !kpis ? <KPICardsSkeleton /> : <KPICards kpis={kpis} volumeTrend={volumeTrend} mttrTrend={mttrTrend} />}

        <div className="chart-grid">
          <VolumeTrendChart data={volumeTrend} />
          <MttrSlaTrendChart data={mttrTrend} />
        </div>

        <div style={{ marginTop: "1.4rem" }}>
          <CustomerHealth onSelectCustomer={focusCustomer} />
        </div>

        <div style={{ marginTop: "1.4rem" }}>
          <IncidentTable incidents={incidents} loading={loading} />
        </div>

        {showNewIncident && (
          <NewIncidentModal
            customers={customers}
            onClose={() => setShowNewIncident(false)}
            onCreated={handleIncidentCreated}
          />
        )}

        {closingTicket && (
          <CloseIncidentModal
            ticket={closingTicket}
            onClose={() => setClosingTicket(null)}
            onClosed={handleIncidentClosed}
          />
        )}

        {showDemoSetup && (
          <DemoSetupWizard onClose={() => setShowDemoSetup(false)} onComplete={handleDemoSetupComplete} />
        )}

        <Confetti trigger={confettiTrigger} />
        <Toast toasts={toasts} />
      </Layout>
    </>
  );
}
