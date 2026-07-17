import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../services/api";

export default function Admin() {
  const [customers, setCustomers] = useState([]);
  const [resetStatus, setResetStatus] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api
      .get("/customers")
      .then((res) => setCustomers(res.data))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleReset() {
    setResetStatus("Reseeding demo data…");
    try {
      await api.post("/demo/reset");
      setResetStatus("Demo data reseeded.");
      load();
    } catch (err) {
      setResetStatus(err.response?.data?.detail || "Reset failed.");
    }
  }

  return (
    <Layout title="Admin — Customers &amp; Demo Controls" latencyMs={null}>
      <div className="table-card" style={{ marginBottom: "1.4rem" }}>
        <h3 style={{ paddingBottom: "1rem" }}>Demo controls</h3>
        <div style={{ padding: "0 1.2rem 1.2rem" }}>
          <button className="btn" onClick={handleReset}>
            Re-seed demo data
          </button>
          {resetStatus && <p style={{ color: "var(--text-soft)" }}>{resetStatus}</p>}
        </div>
      </div>

      <div className="table-card">
        <h3>All customers ({customers.length})</h3>
        {loading ? (
          <div className="loading-state">Loading…</div>
        ) : (
          <table className="incident-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Partner</th>
                <th>Tier</th>
                <th>SIEM</th>
                <th>SOAR</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.customer_id}>
                  <td>{c.customer_name}</td>
                  <td className="mono">{c.partner_id}</td>
                  <td>{c.service_tier}</td>
                  <td>{c.siem}</td>
                  <td>{c.soar}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
