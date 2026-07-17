import { Link } from "react-router-dom";

export default function Unauthorized() {
  return (
    <div className="status-page">
      <div className="code">403</div>
      <h1>You don't have access to this page</h1>
      <p style={{ color: "var(--text-soft)" }}>
        Your role doesn't include this scope. Try the dashboard instead.
      </p>
      <Link className="btn" to="/dashboard">
        Back to dashboard
      </Link>
    </div>
  );
}
