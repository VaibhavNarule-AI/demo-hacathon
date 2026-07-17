import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);

function resolveEffective(mode) {
  if (mode === "system") {
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  return mode;
}

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem("theme") || "dark");
  const [effective, setEffective] = useState(() => resolveEffective(mode));

  useEffect(() => {
    localStorage.setItem("theme", mode);
    setEffective(resolveEffective(mode));

    if (mode !== "system") return undefined;
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => setEffective(resolveEffective("system"));
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [mode]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", effective);
  }, [effective]);

  return (
    <ThemeContext.Provider value={{ mode, setMode, effective }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
