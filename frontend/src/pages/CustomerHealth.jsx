import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ChartCard from "../components/ChartCard";
import CustomerHealthGrid from "../components/CustomerHealth";
import { useApp } from "../context/AppContext";
import api from "../services/api";

export default function CustomerHealth() {
  const navigate = useNavigate();
  const { focusCustomer, refreshKey } = useApp();
  const [anomalies, setAnomalies] = useState([]);
  const [slaTrend, setSlaTrend] = useState([]);

  useEffect(() => {
    api.get("/analytics/customer-health").then((res) => {
      setAnomalies(res.data.filter((c) => c.anomaly));
    }).catch(() => {});
    api.get("/analytics/trends", { params: { metric: "mttr" } }).then((res) => setSlaTrend(res.data)).catch(() => {});
  }, [refreshKey]);

  function goCustomer(customerId) {
    focusCustomer(customerId);
    navigate("/incidents");
  }

  return (
    <>
      {anomalies.length > 0 && (
        <div className="breach-banner">
          📈 Volume spike anomaly detected for {anomalies.length} customer{anomalies.length > 1 ? "s" : ""}:{" "}
          {anomalies.map((a) => a.customer_name).join(", ")} — ticket volume jumped week-over-week.
        </div>
      )}

      <div className="chart-grid" style={{ gridTemplateColumns: "1fr" }}>
        <ChartCard
          title="SLA Compliance Trend"
          subtitle="Overall SLA compliance % across the selected range — the strongest single leading indicator of customer health"
          type="line"
          data={slaTrend.map((p) => ({ week: p.week_start.slice(5), sla: Math.round(p.values.sla_compliance_pct || 0) }))}
          xKey="week"
          series={[{ key: "sla", label: "SLA Compliance %", color: "#34d399" }]}
        />
      </div>

      <CustomerHealthGrid onSelectCustomer={goCustomer} />
    </>
  );
}
