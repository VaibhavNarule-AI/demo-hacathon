export default function Toast({ toasts }) {
  if (toasts.length === 0) return null;
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.kind || "info"}`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}
