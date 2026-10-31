import { expect, test } from "@playwright/test";

test("home customer entry connects to the fixed staff workspace", async ({
  page,
  browser,
}) => {
  await page.goto("/");
  const entry = page.getByRole("link", { name: "ورود مشتری", exact: true });
  await expect(entry).toHaveAttribute("href", "/chat/tarvio-demo");
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(entry).toBeVisible();
    await expect(
      page.getByRole("link", { name: "ورود کارکنان", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
  }
  await page.setViewportSize({ width: 1440, height: 960 });
  await entry.click();
  await expect(page).toHaveURL(/\/chat\/tarvio-demo$/);
  // Route commit precedes visitor-session creation. Wait for the authenticated
  // customer UI before reading identity; otherwise a 401 body yields undefined
  // workspace_id and incorrectly blames the later staff login navigation.
  const create = page.getByRole("button", {
    name: "گفت‌وگوی تازه",
    exact: true,
  });
  await expect(create).toBeVisible();
  const identityResponse = await page.request.get("/api/v1/customer/session");
  expect(identityResponse.status()).toBe(200);
  const identity = await identityResponse.json();
  expect(identity.workspace_id).toMatch(/^[0-9a-f-]{36}$/i);
  await create.click();
  await expect(
    page.getByRole("textbox", { name: "پیام", exact: true }),
  ).toBeVisible();
  const handoff = page.getByRole("button", {
    name: "درخواست کارشناس",
    exact: true,
  });
  if (await handoff.isVisible()) {
    await handoff.click();
    await expect(handoff).toHaveCount(0);
  }
  const body = "بررسی اتصال مشتری به صندوق فضای اصلی";
  await page.getByRole("textbox", { name: "پیام", exact: true }).fill(body);
  await page.getByRole("button", { name: "ارسال", exact: true }).click();
  await expect(
    page.locator(".messages-scroll").getByText(body, { exact: true }),
  ).toBeVisible();
  const [conversation] = await (
    await page.request.get("/api/v1/customer/conversations")
  ).json();
  const snapshot = await (
    await page.request.get(
      `/api/v1/customer/conversations/${conversation.id}/snapshot`,
    )
  ).json();
  expect(snapshot.active_run).toBeNull();

  const staffContext = await browser.newContext({
    baseURL: "http://localhost:5173",
    viewport: { width: 1440, height: 960 },
    locale: "fa-IR",
  });
  try {
    const staff = await staffContext.newPage();
    await staff.goto("/");
    await staff
      .getByRole("link", { name: "ورود کارکنان", exact: true })
      .click();
    await staff
      .getByLabel("ایمیل", { exact: true })
      .fill("admin@tarvio.invalid");
    await staff
      .getByLabel("رمز عبور", { exact: true })
      .fill("Fictional-Demo-Only-2026!");
    await staff
      .getByRole("button", { name: "ورود به میز کار", exact: true })
      .click();
    await expect(staff).toHaveURL(
      new RegExp(`/app/${identity.workspace_id}/inbox$`),
    );
    await staff
      .getByRole("button", {
        name: `گفت‌وگو ${conversation.id.slice(0, 8).toUpperCase()}`,
        exact: true,
      })
      .click();
    await expect(
      staff.locator(".messages-scroll").getByText(body, { exact: true }),
    ).toBeVisible();
    await staff
      .getByRole("button", { name: "پذیرش گفت‌وگو", exact: true })
      .click();
    const reply = "پیام شما در فضای اصلی دریافت شد.";
    await staff.getByRole("textbox", { name: "پیام", exact: true }).fill(reply);
    await staff.getByRole("button", { name: "ارسال", exact: true }).click();
    await expect(
      page.locator(".messages-scroll").getByText(reply, { exact: true }),
    ).toBeVisible();
  } finally {
    await staffContext.close();
  }
});
