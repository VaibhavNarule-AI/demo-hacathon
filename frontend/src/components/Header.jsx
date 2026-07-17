import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { useTimezone } from "../context/TimezoneContext";
import Logo from "./Logo";

const THEME_OPTIONS = [
  { key: "light", label: "Light" },
  { key: "dark", label: "Dark" },
  { key: "system", label: "System" },
];

function initials(username) {
  if (!username) return "?";
  return username.slice(0, 2).toUpperCase();
}

function secondsAgoLabel(lastUpdatedAt, tick) {
  if (!lastUpdatedAt) return "—";
  const secs = Math.max(0, Math.round((tick - lastUpdatedAt) / 1000));
  if (secs < 2) return "just now";
  if (secs < 60) return `${secs} sec ago`;
  return `${Math.round(secs / 60)} min ago`;
}

export default function Header({ onNewIncident, onEnterCommandCenter, onOpenDemoSetup, lastUpdatedAt }) {
  const navigate = useNavigate();
  const { mode, setMode } = useTheme();
  const { tz, setTz } = useTimezone();
  const [tick, setTick] = useState(() => Date.now());

  const role = localStorage.getItem("role") || "unknown";
  const username = localStorage.getItem("username") || role;
  const canCreateIncident = role === "analyst" || role === "super_admin";
  const canManagePartners = role === "super_admin" || role === "partner_manager";

  useEffect(() => {
    const id = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  function logout() {
    localStorage.clear();
    navigate("/login");
  }

  return (
    <div className="topbar">
      <div className="brand">
        <Logo />
        <div className="brand-text">
          <div className="brand-name">PulseSOC</div>
          <div className="brand-sub">SOC Executive Command Center</div>
        </div>
      </div>

      <div className="live-indicator" title="Auto-refreshes every 30s">
        <span className="live-dot" />
        Live · Updated {secondsAgoLabel(lastUpdatedAt, tick)}
      </div>

      <div className="actions">
        {canCreateIncident && (
          <button className="btn" onClick={onNewIncident}>
            + New Incident
          </button>
        )}
        <button className="btn secondary" onClick={onEnterCommandCenter}>
          Command Center
        </button>

        <div className="theme-toggle" role="group" aria-label="Theme">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              className={mode === opt.key ? "active" : ""}
              onClick={() => setMode(opt.key)}
              type="button"
            >
              {opt.label}
            </button>
          ))}
        </div>

        <select
          className="tz-select"
          value={tz}
          onChange={(e) => setTz(e.target.value)}
          title="Times shown in this timezone"
        >
          <option value="IST">IST</option>
          <option value="UTC">UTC</option>
          <option value="EST">EST</option>
        </select>

        {canManagePartners && (
          <a className="btn secondary" href="/partners" style={{ textDecoration: "none" }}>
            Partner Management
          </a>
        )}
        {role === "super_admin" && (
          <>
            <a className="btn secondary" href="/admin" style={{ textDecoration: "none" }}>
              Admin
            </a>
            <button className="btn secondary" onClick={onOpenDemoSetup}>
              Demo Setup
            </button>
          </>
        )}

        <div className="user-menu">
          <div className="avatar">{initials(username)}</div>
          <div className="user-info">
            <div className="user-name">{username}</div>
            <span className="badge role-badge">{role}</span>
          </div>
        </div>

        <button className="btn secondary" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  );
}
