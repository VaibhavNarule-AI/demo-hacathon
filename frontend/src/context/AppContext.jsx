import { createContext, useContext, useEffect, useRef, useState } from "react";
import api from "../services/api";

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

export function defaultFilters(fixedCustomer) {
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

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const fixedCustomer = localStorage.getItem("customer_id") || "";

  // Shared filter state -- persists across pages (Dashboard <-> Incidents etc.)
  const [filters, setFilters] = useState(() => defaultFilters(fixedCustomer));

  // Shared customers list -- fetched once, used by filter bar / modals everywhere
  const [customers, setCustomers] = useState([]);

  // Shared breach-risk poll -- feeds the War Room banner (always visible) and
  // the Breach Predictor page / Dashboard summary widget, without each
  // fetching independently.
  const [breachRisk, setBreachRisk] = useState([]);
  const [breachRiskLoading, setBreachRiskLoading] = useState(true);
  const [breachRiskFetchedAt, setBreachRiskFetchedAt] = useState(Date.now());

  const [toasts, setToasts] = useState([]);
  const toastId = useRef(0);

  const [refreshKey, setRefreshKey] = useState(0);

  // Global overlay state -- New Incident modal, Close/Resolve modal, Demo
  // Setup wizard, and Command Center mode can all be triggered from any page.
  const [showNewIncident, setShowNewIncident] = useState(false);
  const [closingTicket, setClosingTicket] = useState(null);
  const [showDemoSetup, setShowDemoSetup] = useState(false);
  const [showCommandCenter, setShowCommandCenter] = useState(false);
  const [confettiTrigger, setConfettiTrigger] = useState(0);

  function pushToast(message, kind = "info") {
    const id = ++toastId.current;
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500);
  }

  function bumpRefresh() {
    setRefreshKey((k) => k + 1);
  }

  function loadCustomers() {
    api.get("/customers").then((res) => setCustomers(res.data)).catch(() => {});
  }

  function loadBreachRisk() {
    api
      .get("/analytics/breach-risk")
      .then((res) => {
        setBreachRisk(res.data);
        setBreachRiskFetchedAt(Date.now());
        setBreachRiskLoading(false);
      })
      .catch(() => setBreachRiskLoading(false));
  }

  useEffect(loadCustomers, []);

  useEffect(() => {
    loadBreachRisk();
    const id = setInterval(loadBreachRisk, 30_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  function resetFilters() {
    setFilters(defaultFilters(fixedCustomer));
  }

  function focusCustomer(customerId) {
    if (fixedCustomer) return;
    setFilters((f) => ({ ...f, customers: [customerId] }));
  }

  function handleIncidentCreated(incident) {
    setShowNewIncident(false);
    pushToast(`Incident ${incident.ticket_number} created`, "success");
    bumpRefresh();
  }

  function handleIncidentClosed(updated) {
    setClosingTicket(null);
    if (updated.sla_saved_message) {
      pushToast(`${updated.ticket_number} closed — ${updated.sla_saved_message}`, "success");
      setConfettiTrigger((t) => t + 1);
    } else {
      pushToast(`${updated.ticket_number} closed (SLA already breached)`, "error");
    }
    bumpRefresh();
  }

  function handleDemoSetupComplete(partnerId, customerId) {
    setShowDemoSetup(false);
    pushToast(`Demo ready — ${partnerId} / ${customerId} filtered in`, "success");
    loadCustomers();
    setFilters((f) => ({ ...f, customers: [customerId] }));
    bumpRefresh();
  }

  const blinkingTickets = breachRisk
    .filter((r) => r.blinking_critical)
    .map((r) => ({ ...r, fetchedAt: breachRiskFetchedAt }));

  return (
    <AppContext.Provider
      value={{
        filters, setFilters, fixedCustomer, resetFilters, focusCustomer,
        customers, loadCustomers,
        breachRisk, breachRiskLoading, breachRiskFetchedAt, blinkingTickets, reloadBreachRisk: loadBreachRisk,
        toasts, pushToast,
        refreshKey, bumpRefresh,
        showNewIncident, setShowNewIncident,
        closingTicket, setClosingTicket,
        showDemoSetup, setShowDemoSetup,
        showCommandCenter, setShowCommandCenter,
        confettiTrigger,
        handleIncidentCreated, handleIncidentClosed, handleDemoSetupComplete,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
