import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Logo from "../components/Logo";
import api from "../services/api";

const DEMO_USERS = [
  { user: "superadmin", pass: "Admin@123", role: "super_admin", scope: "all partners" },
  { user: "partner_mgr", pass: "Partner@123", role: "partner_manager", scope: "partner-a" },
  { user: "customer_viewer", pass: "Customer@123", role: "customer_viewer", scope: "partner-a / customer-1" },
  { user: "analyst", pass: "Analyst@123", role: "analyst", scope: "partner-a, read-only" },
];

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    console.log("Step 1: login submitted for", username);
    try {
      const res = await api.post("/auth/login", { username, password });
      console.log("Step 2: JWT issued, role =", res.data.role);

      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("username", username);
      localStorage.setItem("role", res.data.role);
      localStorage.setItem("partner_id", res.data.partner_id || "");
      localStorage.setItem("customer_id", res.data.customer_id || "");
      localStorage.setItem("tokenExp", String(Date.now() + 60 * 60 * 1000));

      console.log("Step 3: token stored, redirecting to dashboard");
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-brand">
          <Logo size={36} />
        </div>
        <h1>PulseSOC</h1>
        <p className="sub">SOC Executive Command Center — sign in to view your scoped operational view.</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div>
            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="demo-creds">
          Demo accounts (password shown for the judges only)
          <table>
            <tbody>
              {DEMO_USERS.map((u) => (
                <tr key={u.user}>
                  <td className="mono">{u.user}</td>
                  <td className="mono">{u.pass}</td>
                  <td>{u.scope}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
