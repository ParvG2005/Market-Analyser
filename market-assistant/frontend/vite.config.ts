import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
    // Unit tests are *.test.*; Playwright e2e specs (*.spec.ts) run separately.
    include: ["tests/**/*.test.{ts,tsx}"],
    exclude: ["tests/e2e/**", "node_modules/**"],
  },
});
