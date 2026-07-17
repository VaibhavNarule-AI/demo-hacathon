import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ChartCard from "../components/ChartCard";
import GlobalFilterBar from "../components/GlobalFilterBar";
import IncidentTable from "../components/IncidentTable";
import WarRoomBanner from "../components/WarRoomBanner";
import { useApp } from "../context/AppContext";
import api from "../services/api";

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

export default function Incidents() {
  const { filters, setFilters, resetFilters, fixedCustomer, customers, refreshKey, bumpRefresh, blinkingTickets, setClosingTicket } = useApp();
  const [searchParams, setSearchParams] = useSearchParams();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [severityFilter, setSeverityFilter] = useState(searchParams.get("severity") || "");

  // Query-param-driven filters (from Dashboard chart clicks) applied once on mount.
  useEffect(() => {
    const qCustomer = searchParams.get("customer");
    const qSiem = searchParams.get("siem");
    const qSoar = searchParams.get("soar");
    const qFrom = searchParams.get("from");
    const qTo = searchParams.get("to");
    if (qCustomer || qSiem || qSoar || qFrom || qTo) {
      setFilters((f) => ({
        ...f,
        customers: qCustomer ? [qCustomer] : f.customers,
        siem: qSiem ? [qSiem] : f.siem,
        soar: qSoar ? [qSoar] : f.soar,
        rangePreset: qFrom || qTo ? "custom" : f.rangePreset,
        from: qFrom ? qFrom.slice(0, 10) : f.from,
        to: qTo ? qTo.slice(0, 10) : f.to,
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .get("/incidents/drill-down", { params: toQuery(filters) })
      .then((res) => {
        if (!cancelled) setIncidents(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || "Failed to load incidents.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters, refreshKey]);

  const severityCounts = {};
  incidents.forEach((i) => {
    severityCounts[i.severity] = (severityCounts[i.severity] || 0) + 1;
  });
  const severityData = Object.entries(severityCounts).map(([severity, value]) => ({
    severity,
    value,
    color: SEVERITY_COLORS[severity],
  }));

  const shown = severityFilter ? incidents.filter((i) => i.severity === severityFilter) : incidents;

  function onSeveritySliceClick(slice) {
    setSeverityFilter((cur) => (cur === slice.severity ? "" : slice.severity));
  }

  return (
    <>
      <WarRoomBanner blinkingTickets={blinkingTickets} onTakeAction={(ticket) => setClosingTicket(ticket)} />

      <GlobalFilterBar
        filters={filters}
        onChange={setFilters}
        onReset={() => {
          resetFilters();
          setSeverityFilter("");
          setSearchParams({});
        }}
        customers={customers}
        fixedCustomer={fixedCustomer}
        resultLabel={`${shown.length} of ${incidents.length} incidents`}
      />

      {error && <div className="error-state">{error}</div>}

      <div className="chart-grid" style={{ gridTemplateColumns: "1fr" }}>
        <ChartCard
          title="Filtered Incidents by Severity"
          subtitle="Click a slice to isolate a severity in the table below"
          type="donut"
          data={severityData}
          onSliceClick={onSeveritySliceClick}
          height={140}
        />
      </div>

      {severityFilter && (
        <p style={{ marginBottom: "0.8rem" }}>
          <span className="chip">
            Severity: {severityFilter}
            <button onClick={() => setSeverityFilter("")} aria-label="Clear severity filter">×</button>
          </span>
        </p>
      )}

      <IncidentTable
        incidents={shown}
        loading={loading}
        onRequestClose={(ticket) => setClosingTicket(ticket)}
        onActionDone={bumpRefresh}
      />
    </>
  );
}
