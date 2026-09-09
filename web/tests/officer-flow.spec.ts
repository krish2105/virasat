import { expect, test } from "@playwright/test";

const USER = process.env.E2E_USER ?? "e2e-officer";
const PASS = process.env.E2E_PASS ?? "correct horse battery";

test.describe("officer flow", () => {
  test("login → queue → reject with reason → audit → dossier", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/username|उपयोगकर्ता/i).fill(USER);
    await page.getByLabel(/password|पासवर्ड/i).fill(PASS);
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/\/queue/);
    const rows = page.getByTestId("queue-row");
    await expect(rows.first()).toBeVisible();
    const before = await rows.count();
    await rows.first().click();
    await expect(page).toHaveURL(/\/changes\//);
    await expect(page.getByRole("img", { name: /after|बाद/i })).toBeVisible();
    // reject without a reason must not be possible
    await page.getByTestId("reject").click();
    await expect(page.getByTestId("confirm-reject")).toBeDisabled();
    await page.getByTestId("reject-reason").fill("legal building; mapping lag in the source");
    await page.getByTestId("confirm-reject").click();
    await expect(page).toHaveURL(/\/queue/);
    await expect(rows).toHaveCount(before - 1);
    await page.goto("/audit");
    await expect(page.getByText("decision:reject").first()).toBeVisible();
    await page.goto("/dossier");
    await expect(page.getByTestId("dossier-csv")).toHaveAttribute("href", /dossier\.csv/);
  });

  test("keyboard-only approve", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/username|उपयोगकर्ता/i).fill(USER);
    await page.getByLabel(/password|पासवर्ड/i).fill(PASS);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/queue/);
    await expect(page.getByTestId("queue-row").first()).toBeVisible();
    await page.keyboard.press("j");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/changes\//);
    await page.keyboard.press("a");
    await expect(page).toHaveURL(/\/queue/);
  });
});

test.describe("theme and locale", () => {
  test("theme toggle persists and locale switches to Hindi", async ({ page }) => {
    await page.goto("/");
    const toggle = page.getByTestId("theme-toggle");
    await toggle.click();
    await toggle.click();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await page.reload();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await page.getByTestId("locale-switch").click();
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("शहर");
  });

  test("reduced motion gets a year slider, not a stripped page", async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto("/");
    await expect(page.getByTestId("year-slider")).toBeVisible();
    await page.getByTestId("year-slider").fill("2019");
    await expect(page.getByTestId("year-label")).toHaveText("2019");
    await ctx.close();
  });

  test("no horizontal scroll at 360px", async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 360, height: 740 } });
    const page = await ctx.newPage();
    await page.goto("/");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(overflow).toBe(false);
    await ctx.close();
  });
});
