import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function flatten(data) {
  return (data || []).map((d) => ({ week: d.week_start, ...d.values }));
}

export function VolumeTrendChart({ data }) {
  const rows = flatten(data);
  return (
    <div className="chart-card">
      <h3>Volume — Alerts vs Incidents (weekly)</h3>
      {rows.length === 0 ? (
        <div className="empty-state">No data in the selected range.</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="#24314a" />
            <XAxis dataKey="week" stroke="#9aa8c2" fontSize={12} />
            <YAxis stroke="#9aa8c2" fontSize={12} />
            <Tooltip contentStyle={{ background: "#172238", border: "1px solid #24314a" }} />
            <Bar dataKey="alerts" fill="#3aa0ff" name="Alerts" radius={[4, 4, 0, 0]} />
            <Line
              type="monotone"
              dataKey="incidents"
              stroke="#34d399"
              strokeWidth={2}
              name="Incidents"
              dot={{ r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export function MttrSlaTrendChart({ data }) {
  const rows = flatten(data);
  return (
    <div className="chart-card">
      <h3>MTTR vs SLA Compliance (weekly)</h3>
      {rows.length === 0 ? (
        <div className="empty-state">No data in the selected range.</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="#24314a" />
            <XAxis dataKey="week" stroke="#9aa8c2" fontSize={12} />
            <YAxis yAxisId="hours" stroke="#9aa8c2" fontSize={12} />
            <YAxis yAxisId="pct" orientation="right" stroke="#9aa8c2" fontSize={12} domain={[0, 100]} />
            <Tooltip contentStyle={{ background: "#172238", border: "1px solid #24314a" }} />
            <Line
              yAxisId="hours"
              type="monotone"
              dataKey="avg_mttr_hours"
              stroke="#fbbf24"
              strokeWidth={2}
              name="Avg MTTR (hrs)"
              dot={{ r: 3 }}
            />
            <Line
              yAxisId="pct"
              type="monotone"
              dataKey="sla_compliance_pct"
              stroke="#34d399"
              strokeWidth={2}
              name="SLA Compliance (%)"
              dot={{ r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
