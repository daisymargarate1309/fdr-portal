import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The React dev server (port 5173) forwards /api and /media to Django (port 8000),
// so the browser sees one origin and the Django session cookie works.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/media": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});