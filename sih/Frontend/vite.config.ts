import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5173 is fixed by API_CONTRACT.md Section 7.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
