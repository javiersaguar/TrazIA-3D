import { test } from "@playwright/test";

const SCREENS = ["portada", "proyecto", "pipeline", "revision", "cambios", "bench", "impacto", "proyectos", "familias", "lote", "ajustes"];
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
      // La portada sin la intro del logo, en su estado final
      if (screen === "portada") await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto(screen === "portada" ? "/" : `/${screen}`);
      const thumbs = screen === "proyectos" || screen === "familias";
      if (screen === "portada" || thumbs) {
        // Las secciones y las miniaturas 3D aparecen al entrar en pantalla: se recorre la página antes de la captura completa
        await page.evaluate(async (step) => {
          for (let y = 0; y < document.body.scrollHeight; y += 400) {
            window.scrollTo(0, y);
            await new Promise((r) => setTimeout(r, step));
          }
          window.scrollTo(0, 0);
        }, thumbs ? 600 : 80);
      }
      if (thumbs) {
        // Las miniaturas se dibujan de una en una; sin WebGL la captura sale igual, sin ellas
        await page
          .waitForFunction(() => [...document.querySelectorAll("main figure")].every((f) => f.querySelector("img")), null, { timeout: 30_000 })
          .catch(() => {});
      }
      await page.waitForLoadState("networkidle");
      if (screen === "pipeline") await page.getByText("Pipeline: último trabajo").waitFor({ timeout: 15_000 });
      if (screen === "revision") {
        await page.getByRole("option").first().waitFor();
        await page.keyboard.press("j");
      }
      if (screen === "cambios") {
        await page.getByText("Longitud entre tangentes").first().click();
      }
      await page.waitForTimeout(2500);
      await page.screenshot({ path: `docs/capturas/${screen}-${theme}.png`, fullPage: true });
    });
  }
}
