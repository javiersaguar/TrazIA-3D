import { expect, test } from "@playwright/test";

const base = process.env.NEXT_PUBLIC_API_URL;
test.skip(!base, "Requiere modo API; la demo offline se comprueba en humo.spec.ts");

test("la revisión persiste al recargar y se puede devolver a candidate", async ({ page, request }) => {
  await page.goto("/revision");
  await expect(page.getByRole("listbox", { name: "Campos por revisar" }).getByRole("option").first()).toBeVisible();
  await page.keyboard.press("j");
  await page.keyboard.press("a");
  await expect.poll(async () => (await (await request.get(`${base}/equipment/V-101/revisions/A`)).json()).equipment.diameter.state).toBe("accepted");
  await page.reload();
  await expect(page.getByText("1 de 22")).toBeVisible();
  const current = await request.get(`${base}/equipment/V-101/revisions/A`);
  const restored = await request.patch(`${base}/revisions/A/fields/diameter`, { headers: {
    "If-Match": current.headers()["etag"]!, "Idempotency-Key": `cleanup-${Date.now()}`,
  }, data: { state: "candidate", actor: "Prueba local" } });
  expect(restored.ok()).toBe(true);
  await page.reload();
  await expect(page.getByText("0 de 22")).toBeVisible();
});

test("el visor carga el IFC de la API y conserva sus productos", async ({ page }) => {
  const download = page.waitForResponse(response => response.url().startsWith(base!) && response.url().includes("/ifc?"));
  await page.goto("/revision");
  expect((await download).status()).toBe(200);
  await expect(page.locator('[data-testid="ifc-viewer"][data-phase="ready"]')).toHaveAttribute("data-products", "7");
  await expect(page.getByText("Datos sintéticos · API local")).toBeVisible();
});

test("Pipeline consume SSE y no utiliza el temporizador simulado", async ({ page, request }) => {
  await page.goto("/pipeline");
  await expect(page.getByText("Pipeline: en espera")).toBeVisible();
  const events = page.waitForResponse(response => response.url().startsWith(base!) && response.url().endsWith("/events"));
  await page.getByRole("button", { name: "Procesar demo", exact: true }).click();
  expect((await events).status()).toBe(200);
  await expect(page.getByText(/Pipeline: último trabajo/)).toBeVisible();
  await expect(page.getByRole("cell", { name: /IFC4 DRAFT almacenado/ })).toBeVisible();
  const identity = (await page.getByText(/Trabajo [0-9a-f-]+/).innerText()).replace("Trabajo ", "");
  const job = await (await request.get(`${base}/jobs/${identity}`)).json();
  expect(job.status).toBe("done");
  expect(job.run.seconds).toBeGreaterThan(0);
  await expect(page.getByText("Repetición simulada", { exact: false })).toHaveCount(0);
});
