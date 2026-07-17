import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ThemeProvider } from "./context/ThemeContext";
import { TimezoneProvider } from "./context/TimezoneContext";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider>
      <TimezoneProvider>
        <App />
      </TimezoneProvider>
    </ThemeProvider>
  </React.StrictMode>
);
