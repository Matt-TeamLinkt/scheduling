import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs separately (uvicorn on :8000); in production the API serves
// the built files from web/dist.
export default defineConfig({
  plugins: [react()],
  // Preview builds (VITE_DEMO=1) ship as one script so they can be inlined into a page.
  build: { rollupOptions: { output: { inlineDynamicImports: process.env.VITE_DEMO === "1" } } },
  server: { proxy: { "/api": "http://localhost:8000" } },
});
