import { test, expect } from "@playwright/test";
test.use({ extraHTTPHeaders: { Origin: "http://localhost:5173" } });

test("entry follows public capabilities and recovers without fictional fallback", async ({
  page,
}) => {
  await page.route("**/api/v1/public/capabilities", (route) =>
    route.fulfill({ json: { demo_available: false, ai_mode: "disabled" } }),
  );
  for (const path of ["/", "/demo"]) {
    await page.goto(path);
    await expect(
      page.getByRole("button", { name: "شروع دموی مستقل", exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByText("دموی عمومی فعلاً در دسترس نیست.", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "ورود کارکنان", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "ورود مشتری", exact: true }),
    ).toHaveCount(0);
  }
  await page.unroute("**/api/v1/public/capabilities");
  let failure = true;
  await page.route("**/api/v1/public/capabilities", async (route) => {
    if (failure)
      await route.fulfill({
        status: 503,
        json: { code: "DATABASE_UNAVAILABLE" },
      });
    else await route.continue();
  });
  await page.reload();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "شروع دموی مستقل", exact: true }),
  ).toHaveCount(0);
  failure = false;
  await page.getByRole("button", { name: "تلاش دوباره", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "شروع دموی مستقل", exact: true }),
  ).toBeEnabled();
});

test("inbox searches persisted content beyond its first page and settings redirects", async ({
  page,
}) => {
  await page.goto("/demo");
  await page
    .getByRole("button", { name: "شروع دموی مستقل", exact: true })
    .click();
  await expect(page).toHaveURL(/\/workspace$/);
  const customer = await (
    await page.request.get("/api/v1/customer/session")
  ).json();
  const staff = await (await page.request.get("/api/v1/auth/staff/me")).json();
  const wid = customer.workspace_id;
  expect(
    (
      await page.request.put(`/api/v1/staff/workspaces/${wid}/assistant`, {
        headers: { "X-CSRF-Token": staff.csrf_token },
        data: { enabled: false },
      })
    ).ok(),
  ).toBe(true);
  let target = "";
  const title = "پیگیری پرداخت ابری برای سفارش آزمایشی";
  for (let index = 0; index < 56; index++) {
    const result = await page.request.post("/api/v1/customer/conversations", {
      headers: {
        "X-CSRF-Token": customer.csrf_token,
        "Idempotency-Key": crypto.randomUUID(),
      },
    });
    expect(result.ok()).toBe(true);
    const conversation = await result.json();
    if (index === 0) {
      target = conversation.id;
      const sent = await page.request.post(
        `/api/v1/customer/conversations/${target}/messages`,
        {
          headers: { "X-CSRF-Token": customer.csrf_token },
          data: { client_message_id: crypto.randomUUID(), body: title },
        },
      );
      expect(sent.ok()).toBe(true);
    }
  }
  await page.goto(`/app/${wid}/inbox`);
  const reference = target.slice(0, 8).toUpperCase();
  const targetRow = page.getByRole("button", {
    name: `گفت‌وگو ${reference}`,
    exact: true,
  });
  await expect(targetRow).toHaveCount(0);
  await page
    .getByRole("textbox", { name: "جست‌وجوی متن یا شناسهٔ گفتگو", exact: true })
    .fill("پرداخت ابری");
  await expect(targetRow).toBeVisible();
  await expect(targetRow).toContainText(title);
  await expect(page.locator(".index-header .count")).toHaveCount(0);
  await targetRow.click();
  await expect(page).toHaveURL(new RegExp(`/conversations/${target}$`));
  await expect(
    page.locator(".messages-scroll").getByText(title, { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.locator(".messages-scroll").getByText(title, { exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/app/${wid}/inbox$`));
  await page.goto(`/app/${wid}/settings`);
  await expect(page).toHaveURL(new RegExp(`/app/${wid}/knowledge$`));
  await expect(
    page.getByRole("link", { name: "تنظیمات", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("checkbox", {
      name: "فعال‌سازی دستیار برای گفت‌وگوهای تازه",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "خروج", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  expect((await page.request.get("/api/v1/auth/staff/me")).status()).toBe(401);
  expect((await page.request.get("/api/v1/customer/session")).status()).toBe(
    200,
  );
  await page.goto(`/app/${wid}/inbox`);
  await expect(
    page.getByText("نشست منقضی شده است. دوباره وارد شوید.", { exact: true }),
  ).toBeVisible();
});

test("compact demo label keeps fictional data distinct from live generation", async ({
  page,
}) => {
  await page.route("**/api/v1/public/capabilities", (route) =>
    route.fulfill({ json: { demo_available: true, ai_mode: "live" } }),
  );
  await page.goto("/");
  await expect(page.locator(".demo-indicator")).toHaveCount(1);
  await expect(page.locator(".demo-indicator")).toContainText("دادهٔ نمونه");
  await expect(page.locator(".demo-indicator")).toContainText("مدل زنده");
  await expect(
    page.getByRole("img", {
      name: "تصویر نمونه؛ گفتگوی واقعی نیست",
      exact: true,
    }),
  ).toBeVisible();
});
