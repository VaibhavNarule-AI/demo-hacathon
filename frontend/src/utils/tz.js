import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

export const TIMEZONES = {
  IST: "Asia/Kolkata",
  UTC: "UTC",
  EST: "America/New_York",
};

export function formatInTz(isoString, tzKey, fmt = "MMM D, HH:mm") {
  if (!isoString) return "—";
  const zone = TIMEZONES[tzKey] || "UTC";
  return dayjs.utc(isoString).tz(zone).format(fmt);
}

export function formatTimeOnly(isoString, tzKey) {
  if (!isoString) return "—";
  const zone = TIMEZONES[tzKey] || "UTC";
  return dayjs.utc(isoString).tz(zone).format("h:mm:ss A");
}

export default dayjs;
