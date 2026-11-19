import { test } from "@playwright/test";
import { mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

/*
  Miniaturas de los proyectos de proceso (preview.webp de las tarjetas de Proyectos).
  Abre cada proyecto en su entorno, con la animación quieta para que la imagen sea estable,
  oculta los controles del visor y guarda el lienzo 3D en PNG al doble de resolución.
  No se lanza a mano: scripts/miniaturas_proceso.py compila la web, ejecuta este proyecto
  y reduce cada PNG a WebP de 720 × 380 en web/public/demo/proceso/<id>/preview.webp.
*/
const SALIDA = process.env.MINIATURAS_DIR ?? resolve(__dirname, "../../../generated/miniaturas-proceso");
const CATALOGO = resolve(__dirname, "../../src/features/process-projects/catalog.json");
const ASPECTO = 720 / 380;

type Proyecto = { id: string; code: string };
const proyectos = JSON.parse(readFileSync(CATALOGO, "utf8")) as Proyecto[];

test.use({
  viewport: { width: 1600, height: 1000 },
  deviceScaleFactor: 2,
  colorScheme: "dark",
  launchOptions: {
    args: process.env.PW_CPU_ONLY === "1" ? ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] : undefined,
  },
});

for (const proyecto of proyectos) {
  test(`miniatura ${proyecto.code}`, async ({ page }) => {
    test.setTimeout(150_000);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(`/proyectos-proceso/${proyecto.id}`);
    await page.locator('[data-testid="ifc-viewer"][data-phase="ready"]').waitFor({ timeout: 120_000 });
    await page.waitForLoadState("networkidle");
    // Sombras, mapa de entorno y la transición de la cámara a la vista general.
    await page.waitForTimeout(4_000);
    await page.evaluate(() => {
      const visor = document.querySelector('[data-testid="ifc-viewer"]');
      const lienzo = visor?.querySelector("canvas");
      if (!visor || !lienzo) throw new Error("El visor no tiene lienzo");
      for (const elemento of visor.querySelectorAll<HTMLElement>("*")) {
        if (elemento !== lienzo && !elemento.contains(lienzo)) elemento.style.visibility = "hidden";
      }
    });
    const caja = await page.locator('[data-testid="ifc-viewer"] canvas').first().boundingBox();
    if (!caja) throw new Error("El lienzo no está en pantalla");
    let ancho = caja.width;
    let alto = ancho / ASPECTO;
    if (alto > caja.height) {
      alto = caja.height;
      ancho = alto * ASPECTO;
    }
    mkdirSync(SALIDA, { recursive: true });
    await page.screenshot({
      path: join(SALIDA, `${proyecto.id}.png`),
      clip: {
        x: caja.x + (caja.width - ancho) / 2,
        y: caja.y + (caja.height - alto) * .83,
        width: ancho,
        height: alto,
      },
    });
  });
}
