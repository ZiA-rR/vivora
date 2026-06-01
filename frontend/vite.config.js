import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Vite config:
// - @vitejs/plugin-react   → JSX + Fast Refresh
// - @tailwindcss/vite      → Tailwind v4 (no separate postcss/tailwind config file needed)
// - server.port 5173       → must match the CORS allow_origins in the FastAPI backend
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
  },
});
