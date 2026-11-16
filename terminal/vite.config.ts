import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@public": path.resolve(import.meta.dirname, "charting_library"),
    },
  },
  publicDir: "node_modules/binbot-charts/public",
  server: {
    open: true,
    port: 5173,
    proxy: {
      "/kucoin-futures": {
        target: "https://api-futures.kucoin.com",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/kucoin-futures/, ""),
      },
      "/kucoin": {
        target: "https://api.kucoin.com",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/kucoin/, ""),
      },
      "/binance": {
        target: "https://api.binance.com",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/binance/, ""),
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./setupTests.js"],
    mockReset: true,
  },
});
