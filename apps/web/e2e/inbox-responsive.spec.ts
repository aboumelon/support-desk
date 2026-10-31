import { test, expect, type Page } from "@playwright/test";

// Actual React app, deterministic browser-intercepted API fixtures. No real login,
// backend persistence, provider or ownership authorization is verified here.
test.use({ video: "off" });
const workspace = "fixture-workspace";
const actor = "fixture-operator";
const root = `/app/${workspace}`;
const id = (index: number) =>
  `c${String(index).padStart(7, "0")}-0000-4000-8000-000000000000`;
const now = "2026-10-31T09:00:00Z";
const conversations = Array.from({ length: 35 }, (_, i) => ({
  id: id(i),
  title: `پیگیری درخواست ${i + 1}`,
  last_message_preview: "لطفاً وضعیت پرداخت سفارش آزمایشی را بررسی کنید.",
  status: "open",
  controller: "human",
  assigned_actor_id: actor,
  control_epoch: 1,
  state_version: 1,
  last_event_seq: 50,
  unread_count: i % 3,
  updated_at: now,
}));
const messages = (conversation: string, count = 50) =>
  Array.from({ length: count }, (_, i) => ({
    id: `${conversation}-m${i}`,
    conversation_id: conversation,
    event_seq: i + 1,
    body: `پیام آزمایشی ${i + 1}: پیگیری پرداخت و بررسی وضعیت سفارش. Order REF-${i + 1}`,
    sender_kind: i % 2 ? "agent" : "visitor",
    sender_actor_id: actor,
    client_message_id: null,
    created_at: now,
  }));
async function fixtures(page: Page) {
  await page.routeWebSocket("**/api/v1/realtime/**", () => {});
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/auth/staff/me"))
      return route.fulfill({
        json: {
          audience: "staff",
          csrf_token: "browser-fixture-only",
          actor_id: actor,
          ai_available: true,
          provider_mode: "fake",
          fictional_data: true,
          expires_at: "2099-01-01T00:00:00Z",
          memberships: [
            {
              workspace_id: workspace,
              actor_id: actor,
              role: "admin",
              fictional_data: true,
            },
          ],
        },
      });
    if (path.endsWith("/customer/session"))
      return route.fulfill({ status: 401, json: {} });
    if (path.endsWith("/conversations"))
      return route.fulfill({ json: conversations });
    const conversationId = path.split("/conversations/")[1]?.split("/")[0];
    if (path.endsWith("/snapshot"))
      return route.fulfill({
        json: {
          conversation: conversations.find((c) => c.id === conversationId),
          messages: messages(conversationId!),
          read_cursors: {},
          event_cursor: 50,
          active_run: null,
        },
      });
    if (path.endsWith("/messages") && route.request().method() === "POST")
      return route.fulfill({ status: 503, json: { code: "UNAVAILABLE" } });
    if (path.endsWith("/events") || path.endsWith("/messages"))
      return route.fulfill({ json: [] });
    if (path.endsWith("/read-cursor"))
      return route.fulfill({ json: { last_read_seq: 50 } });
    // Failed transport intentionally exercises existing IndexedDB pending/retry UI.
    return route.fulfill({
      status: 404,
      json: { code: "FIXTURE_NOT_DEFINED" },
    });
  });
}
async function assertNoOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
}
async function anchor(page: Page) {
  return page.locator(".messages-scroll").evaluate((el) => {
    const top = el.getBoundingClientRect().top;
    const node = [
      ...el.querySelectorAll<HTMLElement>("[data-message-id]"),
    ].find((n) => n.getBoundingClientRect().bottom > top)!;
    return {
      id: node.dataset.messageId,
      offset: node.getBoundingClientRect().top - top,
    };
  });
}
for (const [width, indexWidth, railWidth] of [
  [1120, 304, 84],
  [1280, 304, 84],
  [1439, 304, 84],
  [1440, 320, 92],
  [1599, 320, 92],
  [1600, 344, 92],
  [1920, 344, 92],
]) {
  test(`fixture: persistent Inbox geometry at ${width}px`, async ({ page }) => {
    await fixtures(page);
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(`${root}/conversations/${id(0)}`);
    await expect(page.locator("textarea")).toBeVisible();
    await expect(page.locator(".conversation-index")).toBeVisible();
    expect(
      (await page.locator(".conversation-index").boundingBox())!.width,
    ).toBe(indexWidth);
    expect((await page.locator(".rail").boundingBox())!.width).toBe(railWidth);
    await expect(page.locator(".filters")).toHaveAttribute("role", "group");
    for (const name of ["باز", "در صف", "با من", "بسته‌شده"]) {
      const button = page
        .locator(".filters")
        .getByRole("button", { name, exact: true });
      await expect(button).toBeVisible();
      expect((await button.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    }
    await assertNoOverflow(page);
    if ([1120, 1280, 1440, 1920].includes(width))
      await page.screenshot({
        path: test.info().outputPath(`frontend-fixture-inbox-${width}.png`),
      });
  });
}
test("fixture: route Back/Forward preserves query, filter, list scroll and draft below 1120", async ({
  page,
}) => {
  await fixtures(page);
  await page.setViewportSize({ width: 1119, height: 900 });
  await page.goto(`${root}/inbox`);
  await expect(page.locator(".conversation-index")).toBeVisible();
  await expect(page.locator(".reading-pane")).toBeHidden();
  await page
    .locator(".filters")
    .getByRole("button", { name: "با من", exact: true })
    .click();
  await expect(page.locator(".filters [aria-pressed=true]")).toHaveText(
    "با من",
  );
  await page.locator(".search-wrap input").fill("پیگیری");
  await expect
    .poll(() =>
      page.evaluate(() =>
        sessionStorage.getItem(
          `tarvio:draft:staff:fixture-workspace:fixture-operator:inbox-view`,
        ),
      ),
    )
    .toContain("پیگیری");
  await page.waitForTimeout(400); // Existing 300ms search debounce.
  await page.locator(".conversation-list").evaluate((el) => {
    el.scrollTop = 500;
  });
  await page.waitForTimeout(100);
  const row = page.locator(".conversation-row").nth(5);
  await row.click();
  await expect(page).toHaveURL(new RegExp(`/conversations/${id(5)}$`));
  await page.locator("textarea").fill("پیش‌نویس حفظ شود");
  await page.goBack();
  await expect(page.locator(".conversation-index")).toBeVisible();
  await expect(page.locator(".filters [aria-pressed=true]")).toHaveText(
    "با من",
  );
  await expect(page.locator(".search-wrap input")).toHaveValue("پیگیری");
  expect(
    await page.locator(".conversation-list").evaluate((el) => el.scrollTop),
  ).toBeGreaterThan(300);
  await page.goForward();
  await expect(page.locator("textarea")).toHaveValue("پیش‌نویس حفظ شود");
  await page
    .getByRole("button", { name: "بازگشت به فهرست", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`${root}/inbox$`));
  await expect(page.locator(`[data-conversation-id="${id(5)}"]`)).toBeFocused();
  await assertNoOverflow(page);
});
test("fixture: 1119/1120 resize preserves selected detail, reading anchor, draft and pending send", async ({
  page,
}) => {
  await fixtures(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${root}/conversations/${id(0)}`);
  await expect(page.locator("textarea")).toBeVisible();
  await page.locator("textarea").fill("پیام در انتظار ارسال");
  await page.locator(".composer button[type=submit]").click();
  await expect(page.locator(".delivery-note:has(button)")).toHaveCount(1);
  await page.locator("textarea").fill("پیش‌نویس دوم");
  await page.locator(".messages-scroll").evaluate((el) => {
    el.scrollTop = 1200;
  });
  await page.waitForTimeout(100);
  const before = await anchor(page);
  for (const width of [1120, 1119, 1120, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(page.locator(".reading-pane")).toBeVisible();
    await expect(page.locator(".conversation-index"))[
      width < 1120 ? "toBeHidden" : "toBeVisible"
    ]();
    await page.waitForTimeout(100);
    const after = await anchor(page);
    expect(after.id).toBe(before.id);
    expect(Math.abs(after.offset - before.offset)).toBeLessThan(3);
    await expect(page.locator("textarea")).toHaveValue("پیش‌نویس دوم");
    await expect(page.locator(".delivery-note:has(button)")).toHaveCount(1);
    await assertNoOverflow(page);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("textarea")).toHaveValue("پیش‌نویس دوم");
  await assertNoOverflow(page);
  await page.screenshot({
    path: test.info().outputPath("frontend-fixture-inbox-390.png"),
  });
  await page
    .getByRole("button", { name: "بازگشت به فهرست", exact: true })
    .click();
  await page.locator(`[data-conversation-id="${id(0)}"]`).click();
  await expect(page.locator("textarea")).toHaveValue("پیش‌نویس دوم");
  await expect(page.locator(".delivery-note:has(button)")).toHaveCount(1);
  await page.reload();
  await expect(page.locator("textarea")).toHaveValue("پیش‌نویس دوم");
  await expect(page.locator(".delivery-note:has(button)")).toHaveCount(1);
});
for (const width of [390, 768, 1024, 1119]) {
  test(`fixture: direct Inbox is a list at ${width}px even with saved selection`, async ({
    page,
  }) => {
    await fixtures(page);
    await page.addInitScript(
      ({ selected }) =>
        sessionStorage.setItem(
          "tarvio:draft:staff:fixture-workspace:fixture-operator:selection",
          selected,
        ),
      { selected: id(0) },
    );
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`${root}/inbox`);
    await expect(page.locator(".conversation-index")).toBeVisible();
    await expect(page.locator(".reading-pane")).toBeHidden();
    await assertNoOverflow(page);
    if (width === 1119)
      await page.screenshot({
        path: test.info().outputPath("frontend-fixture-list-1119.png"),
      });
  });
}
test("fixture: older transcript anchor is restored after conversation route remount", async ({
  page,
}) => {
  await fixtures(page);
  await page.route("**/snapshot", async (route) => {
    const conversationId = new URL(route.request().url()).pathname
      .split("/conversations/")[1]
      .split("/")[0];
    await route.fulfill({
      json: {
        conversation: conversations.find((c) => c.id === conversationId),
        messages: messages(conversationId, 70).slice(20),
        read_cursors: {},
        event_cursor: 50,
        active_run: null,
      },
    });
  });
  await page.route("**/messages?**", async (route) => {
    const conversationId = new URL(route.request().url()).pathname
      .split("/conversations/")[1]
      .split("/")[0];
    await route.fulfill({ json: messages(conversationId, 70).slice(0, 20) });
  });
  await page.setViewportSize({ width: 1119, height: 900 });
  await page.goto(`${root}/conversations/${id(0)}`);
  await page
    .getByRole("button", { name: "پیام‌های قدیمی‌تر", exact: true })
    .click();
  await expect(page.locator("[data-message-id]")).toHaveCount(70);
  await page.locator(".messages-scroll").evaluate((el) => {
    el.scrollTop = 500;
  });
  await page.waitForTimeout(100);
  const before = await anchor(page);
  await page
    .getByRole("button", { name: "بازگشت به فهرست", exact: true })
    .click();
  await page.locator(`[data-conversation-id="${id(1)}"]`).click();
  await expect(page.locator("textarea")).toBeVisible();
  await page
    .getByRole("button", { name: "بازگشت به فهرست", exact: true })
    .click();
  await page.locator(`[data-conversation-id="${id(0)}"]`).click();
  await expect(page.locator("[data-message-id]")).toHaveCount(70);
  await expect.poll(async () => (await anchor(page)).id).toBe(before.id);
  expect(Math.abs((await anchor(page)).offset - before.offset)).toBeLessThan(3);
});

test("fixture: native filter buttons support keyboard and keep existing query contracts", async ({
  page,
}) => {
  await fixtures(page);
  await page.goto(`${root}/inbox`);
  for (const [name, parameter, value] of [
    ["در صف", "controller", "queue"],
    ["با من", "assigned_actor_id", actor],
    ["بسته‌شده", "status", "resolved"],
  ]) {
    const button = page
      .locator(".filters")
      .getByRole("button", { name, exact: true });
    await button.focus();
    const request = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return (
        url.pathname.endsWith("/conversations") &&
        url.searchParams.get(parameter) === value
      );
    });
    await button.press("Space");
    await request;
    await expect(button).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".filters [aria-pressed=true]")).toHaveCount(1);
    await expect(page.locator(".filters [role=tab]")).toHaveCount(0);
  }
});

async function citationFixture(page: Page) {
  await fixtures(page);
  await page.route("**/snapshot", (route) => {
    const items = messages(id(0));
    items[items.length - 1] = {
      ...items.at(-1)!,
      sender_kind: "assistant",
      body: "پاسخ مستند دربارهٔ درخواست آزمایشی [S1]",
    };
    return route.fulfill({
      json: {
        conversation: conversations[0],
        messages: items,
        read_cursors: {},
        event_cursor: 50,
        active_run: null,
      },
    });
  });
  await page.route("**/citations/**", (route) =>
    route.fulfill({
      json: {
        available: true,
        title: "سند آزمایشی",
        locator: "بخش اول",
        excerpt: "متن منبع آزمایشی برای بررسی چیدمان و دسترس‌پذیری.",
      },
    }),
  );
}
for (const width of [1200, 1280, 1365, 1439]) {
  test(`fixture: staff source does not compress the conversation at ${width}px`, async ({
    page,
  }) => {
    await citationFixture(page);
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(`${root}/conversations/${id(0)}`);
    const chip = page.getByRole("button", { name: "منبع S1", exact: true });
    await expect(chip).toBeVisible();
    await page.locator("textarea").fill("پیش‌نویس هنگام بررسی منبع");
    const before = (await page.locator(".reading-pane").boundingBox())!.width;
    await chip.click();
    const after = (await page.locator(".reading-pane").boundingBox())!.width;
    await test
      .info()
      .attach("source-geometry", {
        body: JSON.stringify({ width, before, after }),
        contentType: "application/json",
      });
    expect(after).toBe(before);
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.locator(".source-inspector")).toHaveCount(0);
    expect(
      (await page.locator(".conversation-index").boundingBox())!.width,
    ).toBe(304);
    await expect(page.getByRole("dialog")).toContainText("متن منبع آزمایشی");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(chip).toBeFocused();
    await expect(page.locator("textarea")).toHaveValue(
      "پیش‌نویس هنگام بررسی منبع",
    );
    await assertNoOverflow(page);
  });
}

test("fixture: source 1439/1440 transition retains citation selection, reader anchor and draft", async ({
  page,
}) => {
  await citationFixture(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${root}/conversations/${id(0)}`);
  await page.locator("textarea").fill("پیش‌نویس محفوظ");
  await page.getByRole("button", { name: "منبع S1", exact: true }).click();
  await expect(
    page.getByRole("complementary", { name: "یادداشت منبع", exact: true }),
  ).toBeVisible();
  await page.locator(".messages-scroll").evaluate((el) => {
    el.scrollTop = 1200;
  });
  await page.waitForTimeout(100);
  const before = await anchor(page);
  await page.setViewportSize({ width: 1439, height: 1000 });
  await expect(page.getByRole("dialog")).toContainText("متن منبع آزمایشی");
  await expect(page.locator(".source-chip")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".source-inspector")).toContainText(
    "متن منبع آزمایشی",
  );
  await expect(page.locator("textarea")).toHaveValue("پیش‌نویس محفوظ");
  await expect.poll(async () => (await anchor(page)).id).toBe(before.id);
  expect(Math.abs((await anchor(page)).offset - before.offset)).toBeLessThan(3);
  await assertNoOverflow(page);
});

test("fixture: login navigation enters staff Inbox without creating a visitor session", async ({
  page,
}) => {
  await fixtures(page);
  let loggedIn = false;
  await page.route("**/auth/staff/me", (route) =>
    loggedIn ? route.fallback() : route.fulfill({ status: 401, json: {} }),
  );
  await page.route("**/auth/staff/login", async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({
      email: "review@example.invalid",
      password: "Synthetic-review-only!",
    });
    loggedIn = true;
    return route.fulfill({
      json: { memberships: [{ workspace_id: workspace }] },
    });
  });
  const visitorMutations: string[] = [];
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      /\/api\/v1\/(public\/demo|customer\/)/.test(request.url())
    )
      visitorMutations.push(request.url());
  });
  await page.goto("/login");
  await page
    .getByLabel("ایمیل", { exact: true })
    .fill("review@example.invalid");
  await page
    .getByLabel("رمز عبور", { exact: true })
    .fill("Synthetic-review-only!");
  await page
    .getByRole("button", { name: "ورود به میز کار", exact: true })
    .click();
  await expect(page).toHaveURL(`${root}/inbox`);
  await expect(
    page.getByRole("heading", { name: "صندوق گفتگو", exact: true }),
  ).toBeVisible();
  await page.locator(`[data-conversation-id="${id(1)}"]`).click();
  await expect(page).toHaveURL(`${root}/conversations/${id(1)}`);
  await expect(page.locator("textarea")).toBeEditable();
  await page.goBack();
  await expect(page).toHaveURL(`${root}/inbox`);
  expect(visitorMutations).toEqual([]);
});

for (const width of [390, 1365]) {
  test(`fixture: customer retains new-conversation control at ${width}px`, async ({
    page,
  }) => {
    await fixtures(page);
    await page.route("**/customer/session", (route) =>
      route.fulfill({
        json: {
          audience: "visitor",
          workspace_id: workspace,
          actor_id: "fixture-visitor",
          csrf_token: "synthetic-only",
          memberships: [],
          public_key: "fixture-public",
          ai_available: true,
          provider_mode: "fake",
          fictional_data: true,
        },
      }),
    );
    await page.route("**/customer/conversations", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({ json: conversations[1] })
        : route.fallback(),
    );
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/workspace");
    const create = page.getByRole("button", {
      name: "گفت‌وگوی تازه",
      exact: true,
    });
    await expect(create).toBeVisible();
    await create.click();
    await expect(page.locator("textarea")).toBeEditable();
    await expect(page.locator(".reading-pane")).toHaveAttribute(
      "aria-label",
      "گفت‌وگو C0000001",
    );
    if (width < 760)
      await page
        .getByRole("button", { name: "بازگشت به فهرست", exact: true })
        .click();
    await expect(create).toBeVisible();
    await assertNoOverflow(page);
  });
}
