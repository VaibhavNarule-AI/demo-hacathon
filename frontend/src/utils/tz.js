// Zero third-party: native Intl.DateTimeFormat only, no dayjs/moment.
// Backend stores UTC-aware ISO strings (explicit +00:00 offset), which the
// native Date constructor parses correctly without any extra handling.

export const TIMEZONES = {
  IST: "Asia/Kolkata",
  UTC: "UTC",
  EST: "America/New_York",
  GMT: "Europe/London",
};

function partsFor(date, zone, opts) {
  const dtf = new Intl.DateTimeFormat("en-US", { timeZone: zone, ...opts });
  const out = {};
  for (const p of dtf.formatToParts(date)) out[p.type] = p.value;
  return out;
}

export function formatInTz(isoString, tzKey, includeSeconds = false) {
  if (!isoString) return "—";
  const zone = TIMEZONES[tzKey] || "UTC";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";
  const p = partsFor(date, zone, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: includeSeconds ? "2-digit" : undefined,
    hour12: false,
  });
  return includeSeconds
    ? `${p.month} ${p.day}, ${p.hour}:${p.minute}:${p.second}`
    : `${p.month} ${p.day}, ${p.hour}:${p.minute}`;
}

export function formatTimeOnly(isoString, tzKey) {
  if (!isoString) return "—";
  const zone = TIMEZONES[tzKey] || "UTC";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
  return dtf.format(date);
}

export function formatDateOnly(isoString, tzKey) {
  if (!isoString) return "—";
  const zone = TIMEZONES[tzKey] || "UTC";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";
  const p = partsFor(date, zone, { year: "numeric", month: "short", day: "2-digit" });
  return `${p.month} ${p.day}, ${p.year}`;
}
