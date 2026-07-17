import { createContext, useContext, useState } from "react";
import { formatInTz, formatTimeOnly } from "../utils/tz";

const TimezoneContext = createContext(null);

export function TimezoneProvider({ children }) {
  const [tz, setTz] = useState(() => localStorage.getItem("tz") || "IST");

  function updateTz(next) {
    localStorage.setItem("tz", next);
    setTz(next);
  }

  const fmt = (iso, pattern) => formatInTz(iso, tz, pattern);
  const fmtTime = (iso) => formatTimeOnly(iso, tz);

  return (
    <TimezoneContext.Provider value={{ tz, setTz: updateTz, fmt, fmtTime }}>
      {children}
    </TimezoneContext.Provider>
  );
}

export function useTimezone() {
  return useContext(TimezoneContext);
}
