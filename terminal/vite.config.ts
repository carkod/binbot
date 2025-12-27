import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  css: {
    preprocessorOptions: {
      scss: {
        quietDeps: true,
      },
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@public": path.resolve(__dirname, "charting_library"),
      "~bootstrap": path.resolve(__dirname, "node_modules/bootstrap"),
    },
  },
  publicDir: "/charting_library",
  define: {
    "process.env": process.env,
  },
  server: {
    open: true,
    proxy: {
      "/kucoin": {
        target: "http://localhost:3001",
        changeOrigin: true,
        // keep path as-is so /kucoin/api/... -> http://localhost:3001/kucoin/api/...
        rewrite: (path) => path,
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
