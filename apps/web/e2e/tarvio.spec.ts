import { expect, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const button = (page: Page, name: string) =>
  page.getByRole("button", { name, exact: true });
const message = (page: Page) =>
  page.getByRole("textbox", { name: "پیام", exact: true });
const ref = (id: string) => id.slice(0, 8).toUpperCase();
async function bootstrap(page: Page) {
  await page.goto("/demo");
  const [bootstrapResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/v1/public/demo") &&
        response.request().method() === "POST",
    ),
    button(page, "شروع دموی مستقل").click(),
  ]);
  const status = bootstrapResponse.status();
  const code = bootstrapResponse.ok()
    ? "OK"
    : (await bootstrapResponse.json()).code;
  expect(
    status,
    `Demo bootstrap must succeed before checking customer controls: HTTP ${status} (${code})`,
  ).toBe(200);
  await expect(button(page, "گفت‌وگوی تازه")).toBeVisible();
  return (await page.request.get("/api/v1/customer/session")).json();
}
async function fresh(page: Page) {
  await button(page, "گفت‌وگوی تازه").click();
  await expect(message(page)).toBeVisible();
}
async function send(page: Page, body: string) {
  await message(page).fill(body);
  await button(page, "ارسال").click();
  await expect(
    page.locator(".messages-scroll").getByText(body, { exact: true }),
  ).toBeVisible();
}
async function snapshot(page: Page, id: string) {
  return (
    await page.request.get(`/api/v1/customer/conversations/${id}/snapshot`)
  ).json();
}

test("Tarvio real workflows preserve drafts, retries, persisted transitions, knowledge and permissions", async ({
  page,
  browser,
}) => {
  test.setTimeout(180000);
  const identity = await bootstrap(page),
    wid = identity.workspace_id;
  await fresh(page);
  const c1 = (
    await (await page.request.get("/api/v1/customer/conversations")).json()
  )[0].id;
  await send(page, "How long is the Tarvio trial? Hand off this turn.");
  await expect(page.getByTestId("ai-draft")).toBeVisible({ timeout: 20000 });
  await button(page, "درخواست کارشناس").click();
  await expect(page.getByTestId("ai-draft")).not.toBeVisible();
  await expect
    .poll(async () => (await snapshot(page, c1)).active_run?.status)
    .toBe("superseded");
  expect(
    (await snapshot(page, c1)).messages.filter(
      (m: { sender_kind: string }) => m.sender_kind === "assistant",
    ),
  ).toHaveLength(0);
  const staffContext = await browser.newContext({
    baseURL: "http://localhost:5173",
    viewport: { width: 1440, height: 1000 },
  });
  await staffContext.addCookies(
    (await page.context().cookies()).filter((c) => c.name === "sd_staff"),
  );
  const staff = await staffContext.newPage();
  await staff.goto(`/app/${wid}/conversations/${c1}`);
  await button(staff, "پذیرش گفت‌وگو").click();
  await send(staff, "پاسخ واقعی کارشناس در نمای تارویو");
  await expect(
    page
      .locator(".messages-scroll")
      .getByText("پاسخ واقعی کارشناس در نمای تارویو", { exact: true }),
  ).toBeVisible();
  await staff.getByLabel("اقدام‌های بیشتر").click();
  await button(staff, "بازگشت به صف").click();
  await button(staff, "پذیرش گفت‌وگو").click();
  await button(staff, "پایان گفت‌وگو").click();
  await button(page, "بازگشایی").click();
  await page.reload();
  await expect(
    page.getByText("گفتگو دوباره باز شد", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("گفتگو به صف کارشناسان بازگردانده شد", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("کارشناس گفتگو را پذیرفت", { exact: true }),
  ).toHaveCount(2);
  await fresh(page);
  const c2 = (
    await (await page.request.get("/api/v1/customer/conversations")).json()
  )[0].id;
  expect(c2).not.toBe(c1);
  const attempts: string[] = [];
  let dropped = false;
  await page.route(
    "**/api/v1/customer/conversations/*/messages",
    async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      attempts.push(route.request().postDataJSON().client_message_id);
      if (!dropped) {
        dropped = true;
        await route.fetch();
        await route.abort("failed");
      } else await route.continue();
    },
  );
  const retryBody =
    "How long is the Tarvio trial? Retry identity verification.";
  await send(page, retryBody);
  await expect(button(page, "تلاش دوباره")).toBeEnabled();
  await button(page, "تلاش دوباره").click();
  await expect(button(page, "تلاش دوباره")).not.toBeVisible();
  expect(attempts.length).toBeGreaterThanOrEqual(2);
  expect(new Set(attempts).size).toBe(1);
  expect(
    (await snapshot(page, c2)).messages.filter(
      (m: { body: string }) => m.body === retryBody,
    ),
  ).toHaveLength(1);
  await page.unroute("**/api/v1/customer/conversations/*/messages");
  await expect(button(page, "منبع S1")).toBeVisible({ timeout: 30000 });
  await message(page).fill("پیش‌نویس اختصاصی گفتگوی دوم");
  await button(page, `گفت‌وگو ${ref(c1)}`).click();
  await expect(message(page)).toHaveValue("");
  await message(page).fill("پیش‌نویس اختصاصی گفتگوی اول");
  await button(page, `گفت‌وگو ${ref(c2)}`).click();
  await expect(message(page)).toHaveValue("پیش‌نویس اختصاصی گفتگوی دوم");
  await page.reload();
  await expect(message(page)).toHaveValue("پیش‌نویس اختصاصی گفتگوی دوم");
  await message(page).fill("");
  await staff.goto(`/app/${wid}/conversations/${c1}`);
  await expect(staff).toHaveURL(new RegExp(`/conversations/${c1}$`));
  await staff.reload();
  await expect(
    staff
      .locator(".messages-scroll")
      .getByText("پاسخ واقعی کارشناس در نمای تارویو", { exact: true }),
  ).toBeVisible();
  await staff.getByRole("button", { name: "در صف", exact: true }).click();
  await expect(button(staff, `گفت‌وگو ${ref(c1)}`)).toBeVisible();
  await expect(button(staff, `گفت‌وگو ${ref(c2)}`)).not.toBeVisible();
  await staff.getByRole("link", { name: "دانش‌نامه", exact: true }).click();
  await button(staff, "افزودن سند").click();
  const modal = staff.getByRole("dialog");
  await modal
    .getByLabel("عنوان سند", { exact: true })
    .fill("Tarvio integration document");
  await modal.getByLabel("فایل سند", { exact: true }).setInputFiles({
    name: "tarvio-policy.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(
      "# Fictional Tarvio integration policy\n\nThis explicitly fictional policy is used for local ingestion verification.",
    ),
  });
  await modal
    .getByRole("button", { name: "بارگذاری و پردازش", exact: true })
    .click();
  const entry = staff
    .locator(".document-entry")
    .filter({ hasText: "Tarvio integration document" });
  await expect(entry.locator(".doc-status")).toHaveText("آماده", {
    timeout: 45000,
  });
  const activation = staff.getByRole("checkbox", {
    name: "فعال‌سازی دستیار برای گفت‌وگوهای تازه",
    exact: true,
  });
  const disabledSetting = staff.waitForResponse(
    (response) =>
      response.url().endsWith(`/workspaces/${wid}/assistant`) &&
      response.request().method() === "PUT",
  );
  await activation.uncheck();
  expect((await disabledSetting).ok()).toBe(true);
  await expect(activation).not.toBeChecked();
  expect(
    (await (await staff.request.get(`/api/v1/staff/workspaces/${wid}`)).json())
      .ai_enabled,
  ).toBe(false);
  const enabledSetting = staff.waitForResponse(
    (response) =>
      response.url().endsWith(`/workspaces/${wid}/assistant`) &&
      response.request().method() === "PUT",
  );
  await activation.check();
  expect((await enabledSetting).ok()).toBe(true);
  await expect(activation).toBeChecked();
  expect(
    (await (await staff.request.get(`/api/v1/staff/workspaces/${wid}`)).json())
      .ai_enabled,
  ).toBe(true);
  await entry.getByRole("button", { name: "نسخهٔ تازه", exact: true }).click();
  await staff
    .getByRole("dialog")
    .getByLabel("فایل سند", { exact: true })
    .setInputFiles({
      name: "invalid-encoding.txt",
      mimeType: "text/plain",
      buffer: Buffer.from([0xff, 0xfe, 0x80, 0x81]),
    });
  await staff
    .getByRole("dialog")
    .getByRole("button", { name: "بارگذاری و پردازش", exact: true })
    .click();
  await expect(entry.locator(".doc-status")).toHaveText("ناموفق", {
    timeout: 45000,
  });
  await expect(
    entry.getByText("نسخهٔ آمادهٔ قبلی همچنان قابل استفاده است.", {
      exact: true,
    }),
  ).toBeVisible();
  await entry
    .getByRole("button", { name: "خارج‌کردن از دانش‌نامه", exact: true })
    .click();
  await button(staff, "تأیید خروج سند").click();
  await expect(entry.locator(".doc-status")).toHaveText("خارج‌شده");
  const trial = staff
    .locator(".document-entry")
    .filter({ hasText: "Fictional fixture: trial" });
  await trial
    .getByRole("button", { name: "خارج‌کردن از دانش‌نامه", exact: true })
    .click();
  await button(staff, "تأیید خروج سند").click();
  await button(page, "منبع S1").click();
  await expect(
    page.getByRole("complementary", { name: "یادداشت منبع" }),
  ).toContainText("این منبع دیگر در دسترس نیست.");
  await button(page, "بستن یادداشت").click();
  const email = `agent-${Date.now()}@integration.invalid`,
    password = "Fictional-Tarvio-Agent-2026!";
  execFileSync(
    fileURLToPath(new URL("../../backend/.venv/bin/python", import.meta.url)),
    [
      "-c",
      [
        "import asyncio, os",
        "from uuid import UUID",
        "from supportdesk.main import create_app",
        "from supportdesk.config import get_settings",
        "from supportdesk.infrastructure.database import Session, now",
        "from supportdesk.modules.identity.models import StaffUser",
        "from supportdesk.modules.identity.service import passwords",
        "from supportdesk.modules.workspaces.models import Actor, Workspace",
        "create_app()",
        "assert get_settings().app_env != 'production'",
        "hashed=passwords.hash(os.environ['TARVIO_AGENT_PASSWORD'])",
        "async def provision():",
        "    async with Session.begin() as db:",
        "        w=await db.get(Workspace,UUID(os.environ['TARVIO_TEST_WORKSPACE']))",
        "        assert w and w.expires_at and w.expires_at > now()",
        "        user=StaffUser(normalized_email=os.environ['TARVIO_AGENT_EMAIL'],password_hash=hashed)",
        "        db.add(user)",
        "        await db.flush()",
        "        db.add(Actor(workspace_id=w.id,kind='staff',role='agent',user_id=user.id,display_name='Fictional integration agent'))",
        "asyncio.run(provision())",
      ].join("\n"),
    ],
    {
      cwd: fileURLToPath(new URL("../../backend", import.meta.url)),
      env: {
        ...process.env,
        TARVIO_TEST_WORKSPACE: wid,
        TARVIO_AGENT_EMAIL: email,
        TARVIO_AGENT_PASSWORD: password,
      },
    },
  );
  const agentContext = await browser.newContext({
    baseURL: "http://localhost:5173",
    extraHTTPHeaders: { Origin: "http://localhost:5173" },
  });
  const agent = await agentContext.newPage();
  const agentSession = await (
    await agent.request.post("/api/v1/auth/staff/login", {
      data: { email, password },
    })
  ).json();
  expect(agentSession.memberships[0].role).toBe("agent");
  await agent.goto(`/app/${wid}/knowledge`);
  await expect(
    agent.getByText("به این فضای کاری یا بخش دسترسی ندارید.", { exact: true }),
  ).toBeVisible();
  expect(
    (
      await agent.request.get(
        `/api/v1/staff/workspaces/${wid}/knowledge/documents`,
      )
    ).status(),
  ).toBe(403);
  await agent.goto(`/app/${wid}/conversations/${c1}`);
  await button(agent, "پذیرش گفت‌وگو").click();
  await staff.goto(`/app/${wid}/conversations/${c1}`);
  await expect(message(staff)).toBeDisabled();
  const otherContext = await browser.newContext({
    baseURL: "http://localhost:5173",
    extraHTTPHeaders: { Origin: "http://localhost:5173" },
  });
  const other = await otherContext.newPage();
  await other.request.post("/api/v1/public/demo");
  await other.goto(`/app/${wid}/conversations/${c1}`);
  await expect(
    other.getByText("به این فضای کاری یا بخش دسترسی ندارید.", { exact: true }),
  ).toBeVisible();
  expect(
    (
      await other.request.get(`/api/v1/customer/conversations/${c1}/snapshot`)
    ).status(),
  ).toBe(404);
  await agentContext.close();
  await otherContext.close();
  await staffContext.close();
});

test("Tarvio desktop/tablet/mobile panes and accessible source sheets use real data", async ({
  page,
}) => {
  test.setTimeout(150000);
  const identity = await bootstrap(page);
  await fresh(page);
  await send(page, "How long is the Tarvio trial?");
  await expect(button(page, "منبع S1")).toBeVisible({ timeout: 30000 });
  const cid = (
    await (await page.request.get("/api/v1/customer/conversations")).json()
  )[0].id;
  let failSource = true;
  await page.route("**/citations/**", async (route) => {
    if (failSource) {
      failSource = false;
      await route.fulfill({
        status: 503,
        body: "{}",
        contentType: "application/json",
      });
    } else await route.continue();
  });
  await button(page, "منبع S1").click();
  await expect(
    page.getByText("دریافت منبع انجام نشد. دوباره تلاش کنید.", { exact: true }),
  ).toBeVisible();
  await button(page, "تلاش دوباره").click();
  await expect(
    page.getByRole("complementary", { name: "یادداشت منبع" }),
  ).toContainText("fourteen days");
  await button(page, "بستن یادداشت").click();
  const publicKey = identity.public_key;
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto(`/chat/${publicKey}`);
    await expect(message(page)).toBeVisible();
    await expect(button(page, "منبع S1")).toBeVisible();
    await page.screenshot({
      path: `../../docs/evidence/portfolio/customer-${width}.png`,
      fullPage: true,
    });
    await button(page, "منبع S1").click();
    if (width < 1200) {
      await expect(page.getByRole("dialog")).toBeVisible();
      await expect(page.getByRole("dialog")).toHaveAttribute(
        "aria-modal",
        "true",
      );
      await page.keyboard.press("Shift+Tab");
      expect(
        await page
          .getByRole("dialog")
          .evaluate((node) => node.contains(document.activeElement)),
      ).toBe(true);
      await page.screenshot({
        path: `../../docs/evidence/portfolio/source-${width}.png`,
        fullPage: true,
      });
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).not.toBeVisible();
      await expect(button(page, "منبع S1")).toBeFocused();
    } else {
      await expect(
        page.getByRole("complementary", { name: "یادداشت منبع" }),
      ).toBeVisible();
      await button(page, "بستن یادداشت").click();
    }
    await page.goto(`/app/${identity.workspace_id}/conversations/${cid}`);
    await expect(message(page)).toBeVisible();
    await page.screenshot({
      path: `../../docs/evidence/portfolio/operator-${width}.png`,
      fullPage: true,
    });
    expect(
      await page
        .locator("body")
        .evaluate((node) => node.scrollWidth <= window.innerWidth),
    ).toBe(true);
    await page.getByRole("link", { name: "دانش‌نامه", exact: true }).click();
    await expect(
      page.getByText("Fictional fixture: trial", { exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: `../../docs/evidence/portfolio/knowledge-${width}.png`,
      fullPage: true,
    });
    expect(
      await page
        .locator("body")
        .evaluate((node) => node.scrollWidth <= window.innerWidth),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 390, height: 520 });
  await page.goto(`/chat/${publicKey}`);
  await message(page).focus();
  await expect(button(page, "ارسال")).toBeInViewport();
});

test("persisted conversation timeline loads multiple authorized event pages in sequence", async ({
  page,
}) => {
  test.setTimeout(90000);
  const identity = await bootstrap(page);
  await fresh(page);
  const cid = (
    await (await page.request.get("/api/v1/customer/conversations")).json()
  )[0].id;
  const prefix = `/api/v1/staff/workspaces/${identity.workspace_id}/conversations/${cid}`;
  const staff = await (await page.request.get("/api/v1/auth/staff/me")).json();
  const current = await snapshot(page, cid);
  const handed = await page.request.post(
    `/api/v1/customer/conversations/${cid}/handoff`,
    {
      headers: {
        Origin: "http://localhost:5173",
        "X-CSRF-Token": identity.csrf_token,
        "Idempotency-Key": crypto.randomUUID(),
      },
      data: { expected_state_version: current.conversation.state_version },
    },
  );
  expect(handed.status()).toBe(200);
  let version = (await handed.json()).state_version;
  await send(page, "پیام واقعی برای بررسی صفحه‌بندی تاریخچه");
  for (let cycle = 0; cycle < 52; cycle++) {
    for (const action of ["claim", "release"]) {
      const response = await page.request.post(`${prefix}/${action}`, {
        headers: {
          Origin: "http://localhost:5173",
          "X-CSRF-Token": staff.csrf_token,
          "Idempotency-Key": crypto.randomUUID(),
        },
        data: { expected_state_version: version },
      });
      expect(response.status()).toBe(200);
      version = (await response.json()).state_version;
    }
  }
  await page.reload();
  await expect(page.locator(".timeline-event")).toHaveCount(105, {
    timeout: 30000,
  });
  const sequences = await page
    .locator(".timeline-row[data-seq]")
    .evaluateAll((nodes) =>
      nodes.map((node) => Number(node.getAttribute("data-seq"))),
    );
  expect(sequences).toEqual([...new Set(sequences)].sort((a, b) => a - b));
  await expect(
    page.getByText("گفتگو به صف کارشناسان منتقل شد", { exact: true }),
  ).toBeVisible();
});
