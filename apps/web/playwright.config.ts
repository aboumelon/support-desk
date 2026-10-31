import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
export default defineConfig({
  testDir: "e2e",
  workers: 1,
  // Keep normal logs and expose assertion details through GitHub check annotations.
  // Reporting only: no retries, skips, timeouts or expected outcomes are changed.
  reporter:
    process.env.GITHUB_ACTIONS === "true" ? [["line"], ["github"]] : undefined,
  timeout: 60000,
  use: {
    baseURL: "http://localhost:5173",
    locale: "fa-IR",
    timezoneId: "Asia/Tehran",
    viewport: { width: 1365, height: 1000 },
    launchOptions: {
      executablePath:
        process.env.CHROME_PATH ??
        (existsSync("/usr/bin/google-chrome")
          ? "/usr/bin/google-chrome"
          : undefined),
      args: ["--no-sandbox"],
    },
    trace: "retain-on-failure",
    video: "on",
  },
});
