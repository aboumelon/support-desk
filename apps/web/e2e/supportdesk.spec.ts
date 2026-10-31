import {
  createPublicSession,
  paceSessionCreation,
  test,
  expect,
} from "./fixtures";

test("isolated customer and operator complete persistent assistant and human chat", async ({
  browser,
  page,
}) => {
  await page.goto("/demo");
  await createPublicSession(page, () =>
    page.getByRole("button", { name: "شروع دموی مستقل", exact: true }).click(),
  );
  await page
    .getByRole("button", { name: "گفت‌وگوی تازه", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "پیام", exact: true })
    .fill("How long is the Tarvio trial?");
  await page.getByRole("button", { name: "ارسال", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "منبع S1", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "منبع S1", exact: true }).click();
  await expect(
    page.getByRole("complementary", { name: "یادداشت منبع" }),
  ).toContainText("fourteen days");
  await page.getByRole("button", { name: "بستن یادداشت", exact: true }).click();
  await page.reload();
  await expect(
    page
      .locator(".messages-scroll")
      .getByText("How long is the Tarvio trial?", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "درخواست کارشناس", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "درخواست کارشناس", exact: true }),
  ).not.toBeVisible();
  const staffContext = await browser.newContext({
    baseURL: "http://localhost:5173",
    viewport: { width: 1365, height: 1000 },
    locale: "fa-IR",
  });
  const cookies = (await page.context().cookies()).filter(
    (cookie) => cookie.name === "sd_staff",
  );
  await staffContext.addCookies(cookies);
  const staff = await staffContext.newPage();
  const customerIdentity = await (
    await page.request.get("/api/v1/customer/session")
  ).json();
  await staff.goto(`/app/${customerIdentity.workspace_id}/inbox`);
  await staff
    .getByRole("button", { name: "پذیرش گفت‌وگو", exact: true })
    .click();
  await staff
    .getByRole("textbox", { name: "پیام", exact: true })
    .fill("پاسخ کارشناس برای آزمون ماندگاری");
  await staff.getByRole("button", { name: "ارسال", exact: true }).click();
  await expect(
    page
      .locator(".messages-scroll")
      .getByText("پاسخ کارشناس برای آزمون ماندگاری", { exact: true }),
  ).toBeVisible();
  // Phase 1 regression: navigation must retain authenticated scope and draft
  // across the persistent/single-pane boundary without minting new sessions.
  const conversation = (
    await (await page.request.get("/api/v1/customer/conversations")).json()
  )[0];
  const conversationRow = staff.getByRole("button", {
    name: `گفت‌وگو ${conversation.id.slice(0, 8).toUpperCase()}`,
    exact: true,
  });
  await conversationRow.click();
  await expect(staff).toHaveURL(
    `/app/${customerIdentity.workspace_id}/conversations/${conversation.id}`,
  );
  await staff
    .getByRole("textbox", { name: "پیام", exact: true })
    .fill("پیش‌نویس بررسی ناوبری");
  await staff.setViewportSize({ width: 1119, height: 1000 });
  await expect(staff.locator(".conversation-index")).toBeHidden();
  await staff
    .getByRole("button", { name: "بازگشت به فهرست", exact: true })
    .click();
  await expect(staff).toHaveURL(`/app/${customerIdentity.workspace_id}/inbox`);
  await expect(conversationRow).toBeVisible();
  await conversationRow.click();
  await expect(
    staff.getByRole("textbox", { name: "پیام", exact: true }),
  ).toHaveValue("پیش‌نویس بررسی ناوبری");
  await staff.setViewportSize({ width: 1120, height: 1000 });
  await expect(staff.locator(".conversation-index")).toBeVisible();
  await staff.goBack();
  await expect(staff).toHaveURL(`/app/${customerIdentity.workspace_id}/inbox`);
  await expect(
    staff.getByRole("textbox", { name: "پیام", exact: true }),
  ).toHaveValue("پیش‌نویس بررسی ناوبری");
  expect((await staff.request.get("/api/v1/auth/staff/me")).status()).toBe(200);
  expect(
    (await (await page.request.get("/api/v1/customer/session")).json())
      .actor_id,
  ).toBe(customerIdentity.actor_id);
  await staff.setViewportSize({ width: 1365, height: 1000 });
  await page.context().setOffline(true);
  await staff
    .getByRole("textbox", { name: "پیام", exact: true })
    .fill("پیام هنگام قطع اتصال مشتری");
  await staff.getByRole("button", { name: "ارسال", exact: true }).click();
  await expect(
    staff
      .locator(".messages-scroll")
      .getByText("پیام هنگام قطع اتصال مشتری", { exact: true }),
  ).toBeVisible();
  await page.context().setOffline(false);
  await expect(
    page
      .locator(".messages-scroll")
      .getByText("پیام هنگام قطع اتصال مشتری", { exact: true }),
  ).toBeVisible({ timeout: 20000 });
  await staff
    .getByRole("button", { name: "پایان گفت‌وگو", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "بازگشایی", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "بازگشایی", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "بازگشایی", exact: true }),
  ).not.toBeVisible();
  await page.reload();
  await expect(
    page
      .locator(".messages-scroll")
      .getByText("پاسخ کارشناس برای آزمون ماندگاری", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "../../docs/evidence/portfolio/customer-chat.png",
    fullPage: true,
  });
  await staff.screenshot({
    path: "../../docs/evidence/portfolio/operator-inbox.png",
    fullPage: true,
  });
  await staff.getByRole("link", { name: "دانش‌نامه", exact: true }).click();
  await expect(
    staff.getByText("Fictional fixture: trial", { exact: true }),
  ).toBeVisible();
  await staff.screenshot({
    path: "../../docs/evidence/portfolio/knowledge.png",
    fullPage: true,
  });
  const staffIdentity = await (
    await staff.request.get("/api/v1/auth/staff/me")
  ).json();
  const details = await (
    await staff.request.get(
      `/api/v1/staff/workspaces/${staffIdentity.memberships[0].workspace_id}`,
    )
  ).json();
  const customerContext = await browser.newContext({
    baseURL: "http://localhost:5173",
  });
  await paceSessionCreation(customerContext);
  const customer = await customerContext.newPage();
  await createPublicSession(customer, () =>
    customer.goto(`/chat/${details.public_key}`),
  );
  await customer
    .getByRole("button", { name: "گفت‌وگوی تازه", exact: true })
    .click();
  await customer
    .getByRole("textbox", { name: "پیام", exact: true })
    .fill("How long is the Tarvio trial?");
  await customer.getByRole("button", { name: "ارسال", exact: true }).click();
  await expect(
    customer.getByRole("button", { name: "منبع S1", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  const before = await (
    await customer.request.get("/api/v1/customer/session")
  ).json();
  await customer.reload();
  await expect(
    customer
      .locator(".messages-scroll")
      .getByText("How long is the Tarvio trial?", { exact: true }),
  ).toBeVisible();
  const after = await (
    await customer.request.get("/api/v1/customer/session")
  ).json();
  expect(after.actor_id).toBe(before.actor_id);
  await customerContext.close();
  await staffContext.close();
});

test("staff login opens the authorized workspace inbox directly", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("ایمیل", { exact: true }).fill("admin@tarvio.invalid");
  await page
    .getByLabel("رمز عبور", { exact: true })
    .fill("Fictional-Demo-Only-2026!");
  await page
    .getByRole("button", { name: "ورود به میز کار", exact: true })
    .click();
  await expect(page).toHaveURL(/\/app\/[^/]+\/inbox$/);
  await expect(
    page.getByRole("heading", { name: "صندوق گفتگو", exact: true }),
  ).toBeVisible();
  expect((await page.request.get("/api/v1/customer/session")).status()).toBe(
    401,
  );
});
