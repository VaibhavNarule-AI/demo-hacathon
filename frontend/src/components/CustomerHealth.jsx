import { useEffect, useState } from "react";
import api from "../services/api";

const STATUS_COLOR = {
  Healthy: "var(--good)",
  "At Risk": "var(--warn)",
  Critical: "var(--bad)",
};

function HealthRing({ score, status }) {
  const color = STATUS_COLOR[status] || "var(--text-soft)";
  return (
    <div
      className="health-ring"
      style={{ "--pct": score, "--ring-color": color }}
    >
      <div className="health-ring-inner">{Math.round(score)}</div>
    </div>
  );
}

export default function CustomerHealth({ onSelectCustomer }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/analytics/customer-health").then((res) => {
      setData(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  return (
    <div className="table-card health-section">
      <div className="health-header">
        <h3>Customer Health — QBR Ready</h3>
        <button className="btn secondary" onClick={() => window.print()}>
          Export PDF
        </button>
      </div>

      {loading ? (
        <div className="skeleton-grid">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skeleton-block" style={{ height: 120 }} />
          ))}
        </div>
      ) : (
        <div className="health-grid">
          {data.map((c) => (
            <div
              key={c.customer_id}
              className="health-card"
              onClick={() => onSelectCustomer(c.customer_id)}
              title={`${c.breaches} SLA breaches · ${c.fp_rate}% false-positive rate · ${c.avg_mttr_h}h avg MTTR (last 30 days)`}
            >
              <HealthRing score={c.health_score} status={c.status} />
              <div className="health-card-body">
                <div className="health-card-name">{c.customer_name}</div>
                <span
                  className="badge"
                  style={{ color: STATUS_COLOR[c.status], background: "transparent", border: `1px solid ${STATUS_COLOR[c.status]}` }}
                >
                  {c.status}
                </span>
                <div className="health-card-issue">{c.top_issue}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
