import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import BreachPredictorTable from "../components/BreachPredictor";
import ChartCard from "../components/ChartCard";
import WarRoomBanner from "../components/WarRoomBanner";
import { useApp } from "../context/AppContext";

const RISK_ORDER = { BREACHED: 0, BLINKING: 1, HIGH: 2, MEDIUM: 3, LOW: 4, SNOOZED: 5 };
const RISK_COLOR = { BREACHED: "#f87171", BLINKING: "#f87171", HIGH: "#fb923c", MEDIUM: "#fbbf24", LOW: "#34d399", SNOOZED: "#9aa8c2" };

export default function BreachPredictor() {
  const navigate = useNavigate();
  const { breachRisk, breachRiskLoading, focusCustomer, setClosingTicket, blinkingTickets } = useApp();

  const byCustomer = useMemo(() => {
    const map = {};
    breachRisk.forEach((r) => {
      const cur = map[r.customer];
      if (!cur || RISK_ORDER[r.risk] < RISK_ORDER[cur.risk] || (RISK_ORDER[r.risk] === RISK_ORDER[cur.risk] && r.pct > cur.pct)) {
        map[r.customer] = r;
      }
    });
    return Object.entries(map)
      .map(([customer, r]) => ({ customer, pct: Math.round(r.pct), risk: r.risk, color: RISK_COLOR[r.risk] }))
      .sort((a, b) => b.pct - a.pct)
      .slice(0, 10);
  }, [breachRisk]);

  function goCustomer(customerId) {
    focusCustomer(customerId);
    navigate("/incidents");
  }

  return (
    <>
      <WarRoomBanner blinkingTickets={blinkingTickets} onTakeAction={(ticket) => setClosingTicket(ticket)} />

      <div className="chart-grid" style={{ gridTemplateColumns: "1fr" }}>
        <ChartCard
          title="Breach Risk by Customer"
          subtitle="Highest SLA-consumption ticket per customer — click a bar to drill into their incidents"
          type="bar"
          data={byCustomer}
          xKey="customer"
          series={[{ key: "pct", label: "% of SLA window consumed", color: "#3aa0ff" }]}
          onSliceClick={(row) => goCustomer(row.customer)}
        />
      </div>

      <BreachPredictorTable
        risk={breachRisk}
        loading={breachRiskLoading}
        onFocusCustomer={goCustomer}
        onRequestClose={(ticket) => setClosingTicket(ticket)}
      />
    </>
  );
}
