import { useEffect, useRef, useState } from "react";
import api from "../services/api";

const CARD_DEFS = [
  ["alerts", "Alerts", ""],
  ["critical_alerts", "Critical Alerts", ""],
  ["incidents", "Incidents", ""],
  ["avg_mttd_minutes", "Avg MTTD", "min"],
  ["avg_mttr_hours", "Avg MTTR", "hrs"],
  ["sla_compliance_pct", "SLA Compliance", "%"],
  ["sla_breaches", "SLA Breaches", ""],
  ["false_positive_rate_pct", "False-Positive Rate", "%"],
];

export default function CommandCenter({ onExit }) {
  const [kpis, setKpis] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [pulseKeys, setPulseKeys] = useState({});
  const [lastUpdated, setLastUpdated] = useState(Date.now());
  const [tick, setTick] = useState(Date.now());
  const prevRef = useRef({});

  useEffect(() => {
    let cancelled = false;
    function load() {
      Promise.all([api.get("/analytics/kpis"), api.get("/incidents")])
        .then(([kpiRes, incRes]) => {
          if (cancelled) return;
          const newKpis = kpiRes.data;
          const changed = {};
          Object.keys(newKpis).forEach((k) => {
            const prevVal = prevRef.current[k];
            if (prevVal !== undefined && prevVal !== newKpis[k].value) {
              changed[k] = true;
            }
          });
          prevRef.current = Object.fromEntries(
            Object.entries(newKpis).map(([k, v]) => [k, v.value])
          );
          setPulseKeys(changed);
          setKpis(newKpis);
          setIncidents(incRes.data.slice(0, 10));
          setLastUpdated(Date.now());
        })
        .catch(() => {});
    }
    load();
    const id = setInterval(load, 10_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const tickId = setInterval(() => setTick(Date.now()), 1000);
    function onKey(e) {
      if (e.key === "Escape") onExit();
    }
    window.addEventListener("keydown", onKey);
    return () => {
      clearInterval(tickId);
      window.removeEventListener("keydown", onKey);
    };
  }, [onExit]);

  const secondsAgo = Math.max(0, Math.round((tick - lastUpdated) / 1000));
  const tickerText = incidents.length
    ? incidents
        .map((i) => `${i.severity} incident from ${i.customer} · ${i.siem} · ${i.ticket_number}`)
        .join("     •     ")
    : "No recent incident activity";

  return (
    <div className="command-center">
      <div className="cc-header">
        <div className="cc-title">PulseSOC — Command Center</div>
        <div className="cc-timer">Last updated {secondsAgo}s ago</div>
        <button className="btn secondary" onClick={onExit}>
          Exit (Esc)
        </button>
      </div>

      {!kpis ? (
        <div className="cc-loading">Loading command center…</div>
      ) : (
        <div className="cc-grid">
          {CARD_DEFS.map(([key, label, unit]) => {
            const value = kpis[key]?.value;
            return (
              <div key={key} className={`cc-card ${pulseKeys[key] ? "cc-pulse" : ""}`}>
                <div className="cc-label">{label}</div>
                <div className="cc-value">
                  {value === null || value === undefined ? "—" : Number(value).toFixed(unit === "" ? 0 : 1)}
                  {unit && <span className="cc-unit"> {unit}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="cc-ticker">
        <div className="cc-ticker-track">{tickerText}</div>
      </div>
    </div>
  );
}
