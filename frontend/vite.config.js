import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/flow": "http://localhost:8000",
      "/test-report": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
