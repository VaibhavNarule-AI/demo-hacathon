import { useEffect, useState } from "react";
import ChartCard from "../components/ChartCard";
import GlobalFilterBar from "../components/GlobalFilterBar";
import { useApp } from "../context/AppContext";
import api from "../services/api";

// Real MITRE ATT&CK tactic each seeded technique belongs to -- grouping is
// data-driven from the actual 8 techniques seed.py generates, not a fixed
// N-technique-per-tactic grid, since forcing an exact matrix would mean
// inventing techniques nobody ever sees an incident for.
const TACTIC_OF = {
  "T1566 Phishing": "Initial Access",
  "T1078 Valid Accounts": "Initial Access",
  "T1059 Command and Scripting Interpreter": "Execution",
  "T1055 Process Injection": "Privilege Escalation",
  "T1110 Brute Force": "Credential Access",
  "T1021 Remote Services": "Lateral Movement",
  "T1071 Application Layer Protocol": "Command & Control",
  "T1041 Exfiltration Over C2": "Exfiltration",
};
const TACTIC_ORDER = [
  "Initial Access", "Execution", "Privilege Escalation", "Credential Access",
  "Lateral Movement", "Command & Control", "Exfiltration",
];

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

function heatColor(intensity) {
  // 0 -> cool blue, 1 -> hot red
  const r = Math.round(59 + intensity * (248 - 59));
  const g = Math.round(160 - intensity * (160 - 113));
  const b = Math.round(255 - intensity * (255 - 113));
  return `rgb(${r}, ${g}, ${b})`;
}

export default function ThreatLandscape() {
  const { filters, setFilters, resetFilters, fixedCustomer, customers, refreshKey } = useApp();
  const [heatmap, setHeatmap] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get("/analytics/mitre-heatmap", { params: toQuery(filters) })
      .then((res) => {
        if (!cancelled) setHeatmap(res.data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters, refreshKey]);

  const maxCount = Math.max(1, ...heatmap.map((h) => h.count));
  const grouped = TACTIC_ORDER.map((tactic) => ({
    tactic,
    techniques: heatmap.filter((h) => TACTIC_OF[h.technique] === tactic),
  })).filter((g) => g.techniques.length > 0);

  const topTechniques = [...heatmap].sort((a, b) => b.count - a.count).slice(0, 8);

  return (
    <>
      <GlobalFilterBar
        filters={filters}
        onChange={setFilters}
        onReset={resetFilters}
        customers={customers}
        fixedCustomer={fixedCustomer}
        resultLabel={`${heatmap.reduce((s, h) => s + h.count, 0)} technique tags across ${heatmap.length} techniques`}
      />

      <div className="table-card" style={{ marginBottom: "1.4rem", padding: "1.1rem 1.2rem" }}>
        <h3 style={{ padding: 0, marginBottom: "1rem" }}>MITRE ATT&amp;CK Heatmap</h3>
        {loading ? (
          <div className="skeleton-block" style={{ height: 160 }} />
        ) : heatmap.length === 0 ? (
          <div className="empty-state">No technique data for this filter.</div>
        ) : (
          <div className="mitre-grid">
            {grouped.map((g) => (
              <div key={g.tactic} className="mitre-column">
                <div className="mitre-tactic-label">{g.tactic}</div>
                {g.techniques.map((t) => {
                  const intensity = t.count / maxCount;
                  return (
                    <div
                      key={t.technique}
                      className="mitre-cell"
                      style={{ background: heatColor(intensity) }}
                      title={`${t.technique}: ${t.count} incident(s)`}
                    >
                      <div className="mitre-cell-name">{t.technique.split(" ").slice(0, 1)[0]}</div>
                      <div className="mitre-cell-count">{t.count}</div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="chart-grid" style={{ gridTemplateColumns: "1fr" }}>
        <ChartCard
          title="Top Techniques by Volume"
          subtitle="Most frequently observed MITRE ATT&CK techniques in scope"
          type="bar"
          data={topTechniques}
          xKey="technique"
          series={[{ key: "count", label: "Incidents", color: "#f87171" }]}
        />
      </div>
    </>
  );
}
