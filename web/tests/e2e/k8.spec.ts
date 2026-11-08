import { expect, test } from "@playwright/test";
import { resolve } from "node:path";

const api = process.env.NEXT_PUBLIC_API_URL;
test.skip(!api, "La edición estructural requiere la API; no se simulan resultados.");

test("K8: alta desde chat, IFC, confirmación, plano y deshacer", async ({ page, request }) => {
  test.setTimeout(120_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/modelo?vista=editar");
  await expect(page.getByLabel("ID de pieza nueva")).toBeVisible();
  const id = `N${Date.now()}`;
  await page.getByRole("textbox", { name: "Describir el cambio" }).fill(
    `Añade boquilla ${id} diámetro 100 mm proyección 200 mm elevación 4500 mm azimut 45 deg`);
  await page.getByRole("button", { name: "Preparar borrador" }).click();
  await expect(page.getByText(`Alta · nozzles.${id}`, { exact: true })).toBeVisible();
  await page.getByLabel("Persona que propone").fill("Prueba sintética K8");
  await page.getByRole("button", { name: "Validar lote", exact: true }).click();
  await expect(page.getByText("Lista para previsualizar", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Previsualizar", exact: true }).click();
  await expect(page.getByRole("button", { name: /Confirmar y crear/ })).toBeEnabled({ timeout: 60_000 });
  await expect(page.locator('[data-testid="ifc-viewer"]')).toHaveAttribute("data-phase", "ready", {timeout:60_000});
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: resolve("../docs/evidencias/k8/formulario-oscuro.png"), fullPage: true });
  await page.evaluate(() => document.documentElement.setAttribute("data-theme", "light"));
  await page.screenshot({ path: resolve("../docs/evidencias/k8/formulario-claro.png"), fullPage: true });
  await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
  const applied = page.waitForResponse(r => r.url().endsWith("/apply") && r.request().method() === "POST");
  await page.getByRole("button", { name: /Confirmar y crear/ }).click();
  const result = await (await applied).json();
  expect(result.revision_id).toBeTruthy();
  const model = await (await request.get(`${api}/equipment/V-101/revisions/${result.proposal.target_revision}`)).json();
  expect(model.equipment.nozzles.some((n: {id: string}) => n.id === id)).toBe(true);
  await page.getByRole("button", { name: "Generar GA nuevo", exact: true }).click();
  await expect(page.getByRole("link", { name: "Descargar PDF", exact: true })).toBeVisible({ timeout: 60_000 });
  const pdf = await request.get(await page.getByRole("link", { name: "Descargar PDF", exact: true }).getAttribute("href") ?? "");
  expect(pdf.ok()).toBe(true);
  expect(pdf.headers()["x-derived-document"]).toBe("true");
  await page.getByRole("button", { name: "Deshacer", exact: true }).first().click();
  await expect(page.getByRole("region", {name:"Resumen de la propuesta"})).toContainText("Deshacer");
});

test("K8: piezas incompletas y LOD explícito", async ({ page }) => {
  await page.goto("/modelo?vista=editar");
  await page.getByLabel("Tipo de pieza", { exact: true }).selectOption("platforms");
  await page.getByLabel("ID de pieza nueva").fill("PL_K8");
  await page.getByRole("button", { name: "Incluir pieza en la propuesta" }).click();
  await expect(page.getByRole("alert").filter({hasText:"Completa"})).toContainText("Completa");
  await expect(page.getByLabel("Elevar el nivel de detalle a LOD 3")).not.toBeChecked();
});

test("K8: cambiar a una familia cargada conserva su catálogo específico", async ({ page }) => {
  const familyTag = process.env.PW_K8_FAMILY_TAG;
  test.skip(!familyTag, "Requiere una revisión sintética horizontal cargada en la API de prueba.");
  await page.goto("/modelo?vista=editar");
  await page.getByLabel("Equipo", { exact: true }).selectOption({label:`${familyTag} · Recipiente horizontal · FAMILY-TEST`});
  await expect(page.getByLabel("Nuevo valor de horizontal.length")).toBeVisible();
  await expect(page.getByLabel("Pieza: Dirección X", {exact:true})).toBeVisible();
  await expect(page.getByLabel("Revisión base")).toHaveValue("A");
  await page.getByLabel("Nuevo valor de horizontal.length").fill("7000");
  await page.getByLabel("Persona que propone").fill("Prueba sintética K8");
  await page.getByLabel("Motivo del cambio (obligatorio)").fill("Ampliación de recipiente horizontal sintético");
  await page.getByRole("button", {name:"Validar lote",exact:true}).click();
  await expect(page.getByText("Lista para previsualizar", {exact:true}).first()).toBeVisible();
});
