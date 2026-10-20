import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  server: {
    port: 4313,
    strictPort: true,
    host: "127.0.0.1",
    proxy: { "/api": { target: "http://127.0.0.1:4314", changeOrigin: true } },
  },
});
