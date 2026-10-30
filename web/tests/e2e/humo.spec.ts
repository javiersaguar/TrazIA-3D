import { expect, test, type Page } from "@playwright/test";

const connected = Boolean(process.env.NEXT_PUBLIC_API_URL);
const SCREENS = [
  { path: "/proyecto", title: "Resumen" },
  { path: "/pipeline", title: "Pipeline" },
  { path: "/revision", title: "Revisión" },
  { path: "/cambios", title: "Cambios" },
  { path: "/bench", title: "Bench" },
  { path: "/impacto", title: "Impacto" },
  { path: "/estudio", title: "Estudio" },
];

function trackErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("response", (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.url()}`));
  return errors;
}

test("las 7 pantallas cargan sin errores y avisan de que los datos son sintéticos", async ({ page }) => {
  const errors = trackErrors(page);
  for (const s of SCREENS) {
    await page.goto(s.path);
    await expect(page.getByRole("heading", { level: 1, name: s.title })).toBeVisible();
    await expect(page.getByText(connected ? "Datos sintéticos · API local" : "Datos sintéticos · sin backend")).toBeVisible();
  }
  expect(errors, errors.join("\n")).toEqual([]);
});

const SKETCHES = [
  { path: "/proyectos", title: "Proyectos" },
  { path: "/documentos", title: "Documentos" },
  { path: "/modelo", title: "Modelo 3D" },
  { path: "/familias", title: "Familias" },
  { path: "/lote", title: "Lote" },
  { path: "/informes", title: "Informes" },
  { path: "/auditoria", title: "Auditoría" },
  { path: "/ajustes", title: "Ajustes" },
];

test("las secciones en boceto cargan sin errores", async ({ page }) => {
  const errors = trackErrors(page);
  for (const s of SKETCHES) {
    await page.goto(s.path);
    await expect(page.getByRole("heading", { level: 1, name: s.title })).toBeVisible();
  }
  expect(errors, errors.join("\n")).toEqual([]);
});

test("la barra lateral navega entre pantallas", async ({ page }) => {
  await page.goto("/proyecto");
  await page.getByRole("navigation", { name: "Navegación principal" }).getByRole("link", { name: "Cambios" }).click();
  await expect(page).toHaveURL(/\/cambios$/);
  await expect(page.getByRole("heading", { level: 1, name: "Cambios" })).toBeVisible();
});

test("revisión por teclado: J selecciona, A acepta y Ctrl+Z deshace", async ({ page, request }) => {
  await page.goto("/revision");
  const queue = page.getByRole("listbox", { name: "Campos por revisar" });
  await expect(queue.getByRole("option").first()).toBeVisible();

  await page.keyboard.press("j");
  await expect(queue.getByRole("option", { selected: true })).toContainText("Diámetro de la virola");

  await page.keyboard.press("a");
  await expect(page.getByText("Campo aceptado")).toBeVisible();
  await expect(queue.getByText("Aceptado")).toBeVisible();
  await expect(page.getByText("1 de 22")).toBeVisible();

  await page.keyboard.press("Control+z");
  await expect(page.getByText("0 de 22")).toBeVisible();
  if (connected) await expect.poll(async () => (await (await request.get(`${process.env.NEXT_PUBLIC_API_URL}/equipment/V-101/revisions/A`)).json()).equipment.diameter.state).toBe("candidate");
});

test("el menú de comandos lleva a una boquilla", async ({ page }) => {
  await page.goto("/proyecto");
  await page.keyboard.press("Control+k");
  const input = page.getByPlaceholder("Ir a una pantalla, boquilla o campo…");
  await expect(input).toBeVisible();
  await input.fill("boquilla N3");
  await expect(page.getByRole("option", { name: "Boquilla N3", selected: true })).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/revision$/);
});

test("el pipeline repite el recorrido y registra eventos", async ({ page }) => {
  await page.goto("/pipeline");
  if (connected) await page.getByRole("button", { name: "Procesar demo", exact: true }).click();
  await expect(page.getByText("Pipeline: último trabajo")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("cell", { name: "GAD_V-101_revA.pdf" }).first()).toBeVisible();
});

test("los cambios se reproducen paso a paso", async ({ page }) => {
  await page.goto("/cambios");
  await expect(page.getByText("Longitud entre tangentes").first()).toBeVisible();
  await page.getByRole("button", { name: "Reproducir los cambios" }).click();
  await expect(page.getByText(/Paso 1 de \d+/)).toBeVisible();
});


test("el laboratorio 3D sigue leyendo los siete productos del IFC", async ({ page }) => {
  const errors = trackErrors(page);
  await page.goto("/lab/3d");
  await expect(page.getByRole("heading", { level: 1, name: "Laboratorio 3D / TrazIA" })).toBeVisible();
  await expect(page.locator('[data-testid="ifc-viewer"]').first()).toHaveAttribute("data-phase", "ready", { timeout: 30_000 });
  await expect(page.locator('[data-testid="ifc-viewer"]').first()).toHaveAttribute("data-products", "7");
  expect(errors, errors.join("\n")).toEqual([]);
});


test("el panel del copiloto conserva las reglas en modo offline", async ({ page }) => {
  test.skip(connected, "El modo API tiene pruebas de respuesta y error propias");
  await page.goto("/revision");
  await expect(page.getByRole("listbox", { name: "Campos por revisar" }).getByRole("option").first()).toBeVisible();
  await page.keyboard.press("j");
  await page.getByRole("button", { name: "Copiloto", exact: true }).click();
  await expect(page.getByText("Reglas sobre el JSON extraído · modo offline")).toBeVisible();
  await expect(page.getByText("Qué pasa si está mal", { exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Tu pregunta" })).toHaveCount(0);
});
