import { expect, test } from "@playwright/test";

test.describe("Root route", () => {
  test("redirects root visits to a new chat", async ({ page }) => {
    await page.goto("/");

    await page.waitForURL("**/workspace/chats/new");
    await expect(page).toHaveURL(/\/workspace\/chats\/new/);
  });
});
