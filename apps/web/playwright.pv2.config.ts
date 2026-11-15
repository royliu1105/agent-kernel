import { defineConfig, devices } from "@playwright/test";

if (process.env.GITHUB_ACTIONS !== "true" || !process.env.CF2_WEB_PROJECT) {
  throw new Error("Authenticated container acceptance is remote-CI-only");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "pv2-authenticated.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 240_000,
  expect: { timeout: 15_000 },
  reporter: "line",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL,
    actionTimeout: 20_000,
    // Request traces could retain bearer credentials; only explicit UI screenshots are exported.
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
