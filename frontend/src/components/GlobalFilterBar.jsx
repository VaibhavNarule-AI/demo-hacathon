const SIEMS = ["QRADAR", "XSIAM"];
const SOARS = ["XSOAR", "Resilient"];
const TIERS = ["Gold", "Silver", "Bronze"];

export default function GlobalFilterBar({ filters, onChange, onReset, customers, fixedCustomer }) {
  function set(key, value) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <div className="filter-bar">
      <div className="field">
        <label htmlFor="f-customer">Customer</label>
        <select
          id="f-customer"
          value={filters.customer}
          onChange={(e) => set("customer", e.target.value)}
          disabled={!!fixedCustomer}
        >
          <option value="">All customers in scope</option>
          {customers.map((c) => (
            <option key={c.customer_id} value={c.customer_id}>
              {c.customer_name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="f-siem">SIEM</label>
        <select id="f-siem" value={filters.siem} onChange={(e) => set("siem", e.target.value)}>
          <option value="">All</option>
          {SIEMS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="f-soar">SOAR</label>
        <select id="f-soar" value={filters.soar} onChange={(e) => set("soar", e.target.value)}>
          <option value="">All</option>
          {SOARS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="f-tier">Tier</label>
        <select id="f-tier" value={filters.tier} onChange={(e) => set("tier", e.target.value)}>
          <option value="">All</option>
          {TIERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="f-from">From</label>
        <input
          id="f-from"
          type="date"
          value={filters.from}
          onChange={(e) => set("from", e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="f-to">To</label>
        <input id="f-to" type="date" value={filters.to} onChange={(e) => set("to", e.target.value)} />
      </div>
      <button className="btn secondary" onClick={onReset} type="button">
        Reset
      </button>
    </div>
  );
}
