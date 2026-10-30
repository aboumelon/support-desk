import { expect, test, type Page } from "@playwright/test";

const baseURL = process.env.CSP_BASE_URL;
test.use({ baseURL: baseURL ?? "http://localhost:5184" });
test.skip(!baseURL, "Run against the production build with preview:csp");

test("workspace reload and human realtime chat obey the production CSP", async ({
  page,
  browser,
}) => {
  const errors: string[] = [];
  function observe(target: Page) {
    target.on("pageerror", (error) => errors.push(error.message));
    target.on("console", (message) => {
      if (/content security policy|unsafe-eval/i.test(message.text())) {
        errors.push(message.text());
      }
    });
  }
  observe(page);
  const response = await page.goto("/");
  const policy = response?.headers()["content-security-policy"];
  expect(policy).toContain("script-src 'self'");
  expect(policy).not.toContain("unsafe-eval");
  await page
    .getByRole("button", { name: "شروع دموی مستقل", exact: true })
    .click();
  await expect(page).toHaveURL(/\/workspace$/);
  await page.reload();
  await page
    .getByRole("button", { name: "گفت‌وگوی تازه", exact: true })
    .click();
  // Handoff before sending avoids any external provider call in this regression.
  const handoff = page.getByRole("button", {
    name: "درخواست کارشناس",
    exact: true,
  });
  await handoff.click();
  await expect(handoff).toHaveCount(0);
  const body = "آزمون سیاست امنیتی نسخه تولید";
  await page.getByRole("textbox", { name: "پیام", exact: true }).fill(body);
  await page.getByRole("button", { name: "ارسال", exact: true }).click();
  await expect(
    page.locator(".messages-scroll").getByText(body, { exact: true }),
  ).toBeVisible();
  const identity = await (
    await page.request.get("/api/v1/customer/session")
  ).json();
  const [conversation] = await (
    await page.request.get("/api/v1/customer/conversations")
  ).json();
  const snapshot = await (
    await page.request.get(
      `/api/v1/customer/conversations/${conversation.id}/snapshot`,
    )
  ).json();
  expect(snapshot.active_run).toBeNull();
  const staffContext = await browser.newContext({ baseURL, locale: "fa-IR" });
  try {
    await staffContext.addCookies(
      (await page.context().cookies()).filter(
        (cookie) => cookie.name === "sd_staff",
      ),
    );
    const staff = await staffContext.newPage();
    observe(staff);
    await staff.goto(`/app/${identity.workspace_id}/inbox`);
    await expect(
      staff.locator(".messages-scroll").getByText(body, { exact: true }),
    ).toBeVisible();
    await staff
      .getByRole("button", { name: "پذیرش گفت‌وگو", exact: true })
      .click();
    const reply = "پاسخ کارشناس با اتصال زنده";
    await staff.getByRole("textbox", { name: "پیام", exact: true }).fill(reply);
    await staff.getByRole("button", { name: "ارسال", exact: true }).click();
    await expect(
      page.locator(".messages-scroll").getByText(reply, { exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.locator(".messages-scroll").getByText(reply, { exact: true }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  } finally {
    await staffContext.close();
  }
});
