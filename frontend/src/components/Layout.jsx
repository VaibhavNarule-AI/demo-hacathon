import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { useTheme } from "../context/ThemeContext";
import { useTimezone } from "../context/TimezoneContext";
import BreachPredictorCloseModal from "./CloseIncidentModal";
import CommandCenter from "./CommandCenter";
import Confetti from "./Confetti";
import DemoSetupWizard from "./DemoSetupWizard";
import Logo from "./Logo";
import NewIncidentModal from "./NewIncidentModal";
import Toast from "./Toast";
import WarRoomBanner from "./WarRoomBanner";

const NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: "📊" },
  { path: "/breach-predictor", label: "SLA Breach Predictor", icon: "⏰" },
  { path: "/partners", label: "Partner Management", icon: "👥", roles: ["super_admin", "partner_manager"] },
  { path: "/notifications", label: "Notifications", icon: "🔔" },
  { path: "/incidents", label: "Incidents", icon: "🚨" },
  { path: "/admin", label: "Admin", icon: "⚙️", roles: ["super_admin"] },
];

const THEME_OPTIONS = [
  { key: "light", label: "Light" },
  { key: "dark", label: "Dark" },
  { key: "system", label: "System" },
];

function initials(email) {
  if (!email) return "?";
  return email.slice(0, 2).toUpperCase();
}

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { mode, setMode } = useTheme();
  const { tz, setTz } = useTimezone();
  const [tick, setTick] = useState(() => Date.now());
  const {
    customers,
    blinkingTickets,
    setClosingTicket,
    closingTicket,
    showNewIncident,
    setShowNewIncident,
    showDemoSetup,
    setShowDemoSetup,
    showCommandCenter,
    setShowCommandCenter,
    confettiTrigger,
    handleIncidentCreated,
    handleIncidentClosed,
    handleDemoSetupComplete,
    toasts,
  } = useApp();

  const role = localStorage.getItem("role") || "unknown";
  const email = localStorage.getItem("email") || role;
  const canCreateIncident = role === "analyst" || role === "super_admin";

  useEffect(() => {
    const id = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  function logout() {
    localStorage.clear();
    navigate("/login");
  }

  const visibleNav = NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(role));
  const current = NAV_ITEMS.find((item) => item.path === location.pathname);

  if (showCommandCenter) {
    return <CommandCenter onExit={() => setShowCommandCenter(false)} />;
  }

  return (
    <div className="app-shell-v2">
      <WarRoomBanner blinkingTickets={blinkingTickets} onTakeAction={(ticket) => setClosingTicket(ticket)} />

      <aside className="sidebar">
        <div className="sidebar-brand">
          <Logo />
          <div className="brand-name">PulseSOC</div>
        </div>
        <nav className="sidebar-nav">
          {visibleNav.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-link ${location.pathname === item.path ? "active" : ""}`}
            >
              <span className="sidebar-icon">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="avatar">{initials(email)}</div>
          <div className="user-info">
            <div className="user-name">{email}</div>
            <span className="badge role-badge">{role}</span>
          </div>
          <button className="btn secondary" onClick={logout} style={{ width: "100%", marginTop: "0.6rem" }}>
            Log out
          </button>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar-v2">
          <div className="breadcrumb">Dashboard / {current?.label || "…"}</div>

          <div className="actions">
            {canCreateIncident && (
              <button className="btn" onClick={() => setShowNewIncident(true)}>
                + New Incident
              </button>
            )}
            <button className="btn secondary" onClick={() => setShowCommandCenter(true)}>
              Command Center
            </button>
            {role === "super_admin" && (
              <button className="btn secondary" onClick={() => setShowDemoSetup(true)}>
                Demo Setup
              </button>
            )}
            <Link to="/notifications" className="bell-icon" title="Notifications">
              🔔
            </Link>

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

            <select className="tz-select" value={tz} onChange={(e) => setTz(e.target.value)}>
              <option value="IST">IST</option>
              <option value="UTC">UTC</option>
              <option value="EST">EST</option>
              <option value="GMT">GMT</option>
            </select>
          </div>
        </header>

        <main className="page-container-v2">
          <Outlet />
        </main>
      </div>

      {showNewIncident && (
        <NewIncidentModal
          customers={customers}
          onClose={() => setShowNewIncident(false)}
          onCreated={handleIncidentCreated}
        />
      )}
      {closingTicket && (
        <BreachPredictorCloseModal
          ticket={closingTicket}
          onClose={() => setClosingTicket(null)}
          onClosed={handleIncidentClosed}
        />
      )}
      {showDemoSetup && (
        <DemoSetupWizard onClose={() => setShowDemoSetup(false)} onComplete={handleDemoSetupComplete} />
      )}

      <Confetti trigger={confettiTrigger} />
      <Toast toasts={toasts} />
    </div>
  );
}
