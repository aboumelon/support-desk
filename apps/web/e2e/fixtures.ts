import {
  test as base,
  expect,
  type Page,
  type BrowserContext,
} from "@playwright/test";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
export { expect, type Page };

// Five public visitor/demo admissions per 60s share the runner's real identity.
// Pace successful attempts >=13s apart, including across suite/CSP invocations.
// No quota reset, spoofed identity, retry-on-429 or production configuration change.
let queue = Promise.resolve();
export async function admitSession<T>(operation: () => Promise<T>): Promise<T> {
  const ledger = process.env.E2E_QUOTA_LEDGER;
  if (!ledger)
    throw new Error("Set E2E_QUOTA_LEDGER for real backend browser tests");
  let unlock!: () => void;
  const preceding = queue;
  queue = new Promise<void>((resolve) => {
    unlock = resolve;
  });
  await preceding;
  try {
    await mkdir(dirname(ledger), { recursive: true });
    let last = 0;
    try {
      last = Number(await readFile(ledger, "utf8"));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
    if (!Number.isFinite(last)) throw new Error("Corrupt E2E admission ledger");
    const delay = Math.max(0, last + 13000 - Date.now());
    if (delay) await new Promise((resolve) => setTimeout(resolve, delay));
    return await operation();
  } finally {
    // Count failures too. Never retry or hide rejected admissions.
    await writeFile(ledger, String(Date.now())).finally(unlock);
  }
}
export async function paceSessionCreation(context: BrowserContext) {
  await context.route(
    /\/api\/v1\/public\/(demo|workspaces\/[^/]+\/visitor-sessions)$/,
    async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      await admitSession(async () => {
        const response = await route.fetch();
        await route.fulfill({ response });
      });
    },
  );
}
// Await real admission (including quota scheduling) before asserting route/UI readiness.
export async function createPublicSession(
  page: Page,
  action: () => Promise<unknown>,
) {
  const [response] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        /\/api\/v1\/public\/(demo|workspaces\/[^/]+\/visitor-sessions)$/.test(
          new URL(response.url()).pathname,
        ),
    ),
    action(),
  ]);
  const code = response.ok() ? "OK" : (await response.json()).code;
  expect(
    response.status(),
    `Public session bootstrap: HTTP ${response.status()} (${code})`,
  ).toBe(200);
}
export const test = base.extend({
  context: async ({ context }, use) => {
    await paceSessionCreation(context);
    await use(context);
  },
});
