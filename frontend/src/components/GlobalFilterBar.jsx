import { useEffect, useMemo, useState } from "react";

const SIEMS = ["QRADAR", "XSIAM"];
const SIEM_ICON = { QRADAR: "🛡️", XSIAM: "⚡" };
const SOARS = ["XSOAR", "Resilient"];
const TIERS = ["Gold", "Silver", "Bronze"];
export const RANGE_PRESETS = [
  { key: "7d", label: "Last 7 days", days: 7 },
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "90d", label: "Last 90 days", days: 90 },
  { key: "custom", label: "Custom range", days: null },
];

function isoDate(d) {
  return d.toISOString().slice(0, 10);
}

function loadPresets() {
  try {
    return JSON.parse(localStorage.getItem("filterPresets") || "[]");
  } catch {
    return [];
  }
}

export default function GlobalFilterBar({ filters, onChange, onReset, customers, fixedCustomer, resultLabel }) {
  const [draft, setDraft] = useState(filters);
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerOpen, setCustomerOpen] = useState(false);
  const [presets, setPresets] = useState(loadPresets);

  useEffect(() => setDraft(filters), [filters]);

  const grouped = useMemo(() => {
    const byPartner = {};
    customers.forEach((c) => {
      if (customerSearch && !c.customer_name.toLowerCase().includes(customerSearch.toLowerCase())) return;
      (byPartner[c.partner_id] = byPartner[c.partner_id] || []).push(c);
    });
    return byPartner;
  }, [customers, customerSearch]);

  const customerNameById = (id) => customers.find((c) => c.customer_id === id)?.customer_name || id;

  function toggleCustomer(id) {
    setDraft((d) => ({
      ...d,
      customers: d.customers.includes(id) ? d.customers.filter((x) => x !== id) : [...d.customers, id],
    }));
  }

  function togglePill(key, value) {
    const next = { ...draft, [key]: draft[key].includes(value) ? draft[key].filter((x) => x !== value) : [...draft[key], value] };
    setDraft(next);
    onChange(next);
  }

  function setRangePreset(key) {
    if (key === "custom") {
      setDraft((d) => ({ ...d, rangePreset: "custom" }));
      return;
    }
    const preset = RANGE_PRESETS.find((p) => p.key === key);
    const to = new Date();
    const from = new Date(to.getTime() - preset.days * 86400000);
    const next = { ...draft, rangePreset: key, from: isoDate(from), to: isoDate(to) };
    setDraft(next);
    onChange(next);
  }

  function apply() {
    onChange(draft);
    setCustomerOpen(false);
  }

  function removeChip(type, value) {
    let next;
    if (type === "customer") next = { ...draft, customers: draft.customers.filter((x) => x !== value) };
    else if (type === "siem") next = { ...draft, siem: draft.siem.filter((x) => x !== value) };
    else if (type === "soar") next = { ...draft, soar: draft.soar.filter((x) => x !== value) };
    else next = { ...draft, tier: "" };
    setDraft(next);
    onChange(next);
  }

  function savePreset() {
    const name = window.prompt("Save current filters as preset:");
    if (!name) return;
    const next = [...presets.filter((p) => p.name !== name), { name, filters: draft }];
    localStorage.setItem("filterPresets", JSON.stringify(next));
    setPresets(next);
  }

  function loadPreset(name) {
    const p = presets.find((p) => p.name === name);
    if (!p) return;
    setDraft(p.filters);
    onChange(p.filters);
  }

  const activeCount = draft.customers.length + draft.siem.length + draft.soar.length + (draft.tier ? 1 : 0);

  return (
    <div className="filter-bar-v2">
      <div className="filter-row">
        <div className="field ms-field">
          <label title="Filter by customer tenant, scoped to your partner">Customer</label>
          <button
            type="button"
            className="ms-trigger"
            onClick={() => setCustomerOpen((o) => !o)}
            disabled={!!fixedCustomer}
          >
            {fixedCustomer
              ? customerNameById(fixedCustomer)
              : draft.customers.length
              ? `${draft.customers.length} selected`
              : "All customers"}
          </button>
          {customerOpen && !fixedCustomer && (
            <div className="ms-dropdown">
              <input
                className="ms-search"
                placeholder="Search customers…"
                value={customerSearch}
                onChange={(e) => setCustomerSearch(e.target.value)}
                autoFocus
              />
              <div className="ms-list">
                {Object.entries(grouped).map(([partnerId, list]) => (
                  <div key={partnerId} className="ms-group">
                    <div className="ms-group-label">{partnerId}</div>
                    {list.map((c) => (
                      <label key={c.customer_id} className="ms-option">
                        <input
                          type="checkbox"
                          checked={draft.customers.includes(c.customer_id)}
                          onChange={() => toggleCustomer(c.customer_id)}
                        />
                        {c.customer_name}
                      </label>
                    ))}
                  </div>
                ))}
              </div>
              <div className="ms-actions">
                <button className="btn secondary" type="button" onClick={() => setCustomerOpen(false)}>
                  Cancel
                </button>
                <button className="btn" type="button" onClick={apply}>
                  Apply
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="field" title="Filter by SIEM source recorded on the incident">
          <label>SIEM</label>
          <div className="pill-group">
            {SIEMS.map((s) => (
              <button
                key={s}
                type="button"
                className={`pill ${draft.siem.includes(s) ? "active" : ""}`}
                onClick={() => togglePill("siem", s)}
              >
                {SIEM_ICON[s]} {s}
              </button>
            ))}
          </div>
        </div>

        <div className="field" title="Filter by SOAR platform recorded on the incident">
          <label>SOAR</label>
          <div className="pill-group">
            {SOARS.map((s) => (
              <button
                key={s}
                type="button"
                className={`pill ${draft.soar.includes(s) ? "active" : ""}`}
                onClick={() => togglePill("soar", s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label title="Filter by service tier">Tier</label>
          <select
            value={draft.tier}
            onChange={(e) => {
              const next = { ...draft, tier: e.target.value };
              setDraft(next);
              onChange(next);
            }}
          >
            <option value="">All</option>
            {TIERS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label title="Ranges beyond 90 days are rejected server-side for performance">Range</label>
          <select value={draft.rangePreset} onChange={(e) => setRangePreset(e.target.value)}>
            {RANGE_PRESETS.map((p) => (
              <option key={p.key} value={p.key}>{p.label}</option>
            ))}
          </select>
        </div>

        {draft.rangePreset === "custom" && (
          <>
            <div className="field">
              <label>From</label>
              <input type="date" value={draft.from} onChange={(e) => setDraft((d) => ({ ...d, from: e.target.value }))} />
            </div>
            <div className="field">
              <label>To</label>
              <input type="date" value={draft.to} onChange={(e) => setDraft((d) => ({ ...d, to: e.target.value }))} />
            </div>
            <button className="btn" type="button" onClick={apply}>
              Apply
            </button>
          </>
        )}

        <div className="preset-controls">
          <button className="btn secondary" type="button" onClick={savePreset}>
            Save as Preset
          </button>
          {presets.length > 0 && (
            <select defaultValue="" onChange={(e) => e.target.value && loadPreset(e.target.value)}>
              <option value="">Load preset…</option>
              {presets.map((p) => (
                <option key={p.name} value={p.name}>{p.name}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="filter-row chips-row">
        {draft.customers.map((id) => (
          <span key={id} className="chip">
            {customerNameById(id)}
            <button onClick={() => removeChip("customer", id)} aria-label="Remove filter">×</button>
          </span>
        ))}
        {draft.siem.map((s) => (
          <span key={s} className="chip">
            {s}
            <button onClick={() => removeChip("siem", s)} aria-label="Remove filter">×</button>
          </span>
        ))}
        {draft.soar.map((s) => (
          <span key={s} className="chip">
            {s}
            <button onClick={() => removeChip("soar", s)} aria-label="Remove filter">×</button>
          </span>
        ))}
        {draft.tier && (
          <span className="chip">
            {draft.tier}
            <button onClick={() => removeChip("tier")} aria-label="Remove filter">×</button>
          </span>
        )}
        {activeCount > 0 && (
          <button className="btn-link" type="button" onClick={onReset}>
            Clear All
          </button>
        )}
        <span className="result-count">{resultLabel}</span>
      </div>
    </div>
  );
}
