import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
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
  },
  test: {
    globals: true,
    environment: "jsdom",
    mockReset: true,
  },
});
