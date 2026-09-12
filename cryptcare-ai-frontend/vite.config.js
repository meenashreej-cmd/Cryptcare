import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward all /api/v1 calls to the FastAPI backend during development.
      // This eliminates CORS issues — the browser talks to Vite (same origin),
      // Vite forwards to FastAPI on port 8000.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
