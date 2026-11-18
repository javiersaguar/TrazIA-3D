import { test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

/*
  Capturas de docs/GUION_DEMO.md para el pitch (pitch/web) y el ensayo: 1920×1080, tema oscuro.
  Se guardan en docs/capturas/producto/demo-0N-*.png en la raíz del repo.
    cd web; corepack pnpm capturas:guion
  Cada paso que prepara la pantalla es «si se puede»: si la interfaz cambia y un clic no
  encuentra su botón, la captura sale igual y el aviso queda en la salida para revisarla.
*/
const DESTINO = resolve(__dirname, "../../../docs/capturas/producto");
const EJEMPLOS = resolve(__dirname, "../../../examples/documents");
mkdirSync(DESTINO, { recursive: true });

test.use({ viewport: { width: 1920, height: 1080 }, colorScheme: "dark" });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try {
      window.localStorage.setItem("theme", "dark");
    } catch {
      /* sin almacenamiento */
    }
  });
});

async function intentar(paso: string, accion: () => Promise<unknown>) {
  try {
    await accion();
  } catch (error) {
    console.warn(`[guion] no se pudo «${paso}»: ${(error as Error).message.split("\n")[0]}`);
  }
}

async function capturar(page: Page, nombre: string, espera = 2000) {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(espera);
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
    document.querySelectorAll("nextjs-portal").forEach((nodo) => nodo.remove()); // insignia de `next dev`
    window.scrollTo(0, 0);
  });
  await page.screenshot({ path: `${DESTINO}/${nombre}.png` });
}

test("demo-01 · documentos con el GA y la HDM recién añadidos", async ({ page }) => {
  await page.goto("/documentos");
  await intentar("añadir los documentos", () =>
    page.getByLabel("Elegir documentos").setInputFiles([
      `${EJEMPLOS}/GAD_V-101_revA.pdf`,
      `${EJEMPLOS}/HDM_V-101_revA.xlsx`,
    ]),
  );
  await capturar(page, "demo-01-documentos");
});

test("demo-02 · pipeline D a mitad, con la lectura encendida", async ({ page }) => {
  await page.goto("/pipeline");
  const grafo = page.getByLabel("Estrategia del grafo");
  await intentar("elegir D · Híbrido", () => grafo.selectOption("d_hibrido", { timeout: 15_000 }));
  // A mitad del recorrido, donde se encienden los canales de lectura
  await intentar("ir a la lectura", async () => {
    const posicion = page.getByLabel("Posición en el recorrido");
    const maximo = Number(await posicion.getAttribute("max", { timeout: 5_000 }));
    await posicion.fill(String(Math.round(maximo * 0.45)), { timeout: 5_000 });
  });
  await capturar(page, "demo-02-pipeline", 1500);
});

test("demo-03 · revisión con el diámetro seleccionado y su cota en el plano", async ({ page }) => {
  await page.goto("/modelo?vista=revision");
  const cola = page.getByRole("listbox", { name: "Campos por revisar" });
  await intentar("seleccionar el diámetro", async () => {
    await cola.getByRole("option").first().waitFor({ timeout: 15_000 });
    await cola.getByRole("option", { name: /Diámetro de la virola/ }).first().click();
  });
  await intentar("esperar el modelo", () =>
    page.locator('[data-testid="ifc-viewer"][data-phase="ready"]').waitFor({ timeout: 30_000 }),
  );
  await capturar(page, "demo-03-revision", 2500);
});

test("demo-04 · estudio con las recomendaciones y los intervalos", async ({ page }) => {
  await page.goto("/bench?vista=estudio");
  await intentar("esperar la gráfica", () => page.locator("svg").first().waitFor({ timeout: 15_000 }));
  await capturar(page, "demo-04-estudio");
});

test("demo-05 · modelo Iso en Rayos X con la N2 en el inspector", async ({ page }) => {
  await page.goto("/modelo?vista=revision");
  await intentar("esperar el modelo", () =>
    page.locator('[data-testid="ifc-viewer"][data-phase="ready"]').waitFor({ timeout: 30_000 }),
  );
  await intentar("vista Iso", () => page.getByRole("radio", { name: "Iso", exact: true }).first().click());
  await intentar("Rayos X", () => page.getByRole("radio", { name: "Rayos X", exact: true }).first().click());
  await intentar("seleccionar la N2", () =>
    page
      .getByRole("listbox", { name: "Campos por revisar" })
      .getByRole("option", { name: /\bN2\b/ })
      .first()
      .click({ timeout: 5_000 }),
  );
  await capturar(page, "demo-05-modelo", 2500);
});

test("demo-06 · cambios con la N4 seleccionada y su impacto", async ({ page }) => {
  await page.goto("/modelo?vista=cambios");
  await intentar("esperar el visor", () =>
    page.locator('[data-testid="revision-morph"][data-phase="ready"]').waitFor({ timeout: 30_000 }),
  );
  // Con «Seguir el cambio» la cámara entra hasta la boquilla y el modelo sale cortado: vista general
  await intentar("vista general", () =>
    page.getByRole("button", { name: "Vista general", exact: true }).click({ timeout: 5_000 }),
  );
  await intentar("dejar de seguir el cambio", async () => {
    const seguir = page.getByRole("button", { name: "Seguir el cambio", exact: true });
    if ((await seguir.getAttribute("aria-pressed", { timeout: 5_000 })) === "true") await seguir.click();
  });
  await intentar("seleccionar la N4", () =>
    page.getByText("N4 · boquilla nueva", { exact: true }).first().click({ timeout: 15_000 }),
  );
  await intentar("esperar la transición", () =>
    page.locator('[data-testid="revision-morph"][data-phase="ready"]').waitFor({ timeout: 30_000 }),
  );
  await capturar(page, "demo-06-cambios", 3000);
});
