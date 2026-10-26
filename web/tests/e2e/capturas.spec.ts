import { test } from "@playwright/test";

const SCREENS = ["proyecto", "pipeline", "revision", "cambios", "bench", "impacto"];
const THEMES = ["oscuro", "claro"] as const;

for (const theme of THEMES) {
  for (const screen of SCREENS) {
    test(`captura ${screen} · ${theme}`, async ({ page }) => {
      await page.addInitScript((t) => {
        try {
          window.localStorage.setItem("theme", t === "claro" ? "light" : "dark");
        } catch {
          /* sin almacenamiento */
        }
      }, theme);
      await page.goto(`/${screen}`);
      await page.waitForLoadState("networkidle");
      if (screen === "pipeline") await page.getByText("Pipeline: último trabajo").waitFor({ timeout: 15_000 });
      if (screen === "revision") {
        await page.getByRole("option").first().waitFor();
        await page.keyboard.press("j");
      }
      if (screen === "cambios") {
        await page.getByText("Longitud entre tangentes").first().click();
      }
      await page.waitForTimeout(600);
      await page.screenshot({ path: `docs/capturas/${screen}-${theme}.png`, fullPage: true });
    });
  }
}
