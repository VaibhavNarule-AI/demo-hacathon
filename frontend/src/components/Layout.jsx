import Header from "./Header";

export default function Layout({
  latencyMs,
  onNewIncident,
  onEnterCommandCenter,
  onOpenDemoSetup,
  lastUpdatedAt,
  children,
}) {
  const role = localStorage.getItem("role") || "unknown";
  const partnerId = localStorage.getItem("partner_id") || "*";
  const customerId = localStorage.getItem("customer_id");
  const scope = customerId ? `${partnerId} / ${customerId}` : partnerId || "*";

  return (
    <div className="app-shell">
      <Header
        onNewIncident={onNewIncident}
        onEnterCommandCenter={onEnterCommandCenter}
        onOpenDemoSetup={onOpenDemoSetup}
        lastUpdatedAt={lastUpdatedAt}
      />
      <div className="page-container">{children}</div>
      <div className="role-footer">
        Role: {role} | Scope: {scope} | Latency: {latencyMs !== null ? `${latencyMs}ms` : "—"}
      </div>
    </div>
  );
}
