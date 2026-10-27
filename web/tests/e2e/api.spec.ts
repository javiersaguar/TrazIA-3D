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
  await expect(page.getByText(/Pipeline: último trabajo/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("cell", { name: /IFC4 DRAFT almacenado/ })).toBeVisible();
  const identity = (await page.getByText(/Trabajo [0-9a-f-]+/).innerText()).replace("Trabajo ", "");
  const job = await (await request.get(`${base}/jobs/${identity}`)).json();
  expect(job.status).toBe("done");
  expect(job.run.seconds).toBeGreaterThan(0);
  await expect(page.getByText("Repetición simulada", { exact: false })).toHaveCount(0);
});


test("el copiloto muestra citas y escribir preguntas no modifica la revisión", async ({ page, request }) => {
  const before = await (await request.get(`${base}/equipment/V-101/revisions/A`)).json();
  await page.route("**/copiloto", async route => {
    const body = route.request().postDataJSON();
    expect(body.path).toBe("diameter");
    expect(body.question).toContain("aceptar");
    await route.fulfill({ json: {
      abstained: false, reason: null, read_only: true, model: "fixture de interfaz",
      revision_id: "DEMO-PLANT:vessel-001:A", revision_version: 1,
      input_sha256: "0".repeat(64), prompt_sha256: "1".repeat(64), tools_used: ["read_evidence"],
      statements: [{ text: "Respuesta de prueba de interfaz: diámetro 2000 mm.", citations: ["test-source"] }], proposals: [],
      citations: [{ id: "test-source", kind: "evidence", title: "Original de prueba · GAD_V-101_revA.pdf", excerpt: "DIAMETER = 2000 mm",
        path: "diameter", document_id: "GA-V101", filename: "GAD_V-101_revA.pdf", page: 1, bbox: [0.4, 0.2, 0.6, 0.3],
        sha256: "2".repeat(64), sheet: null, cell: null, original_verified: true }],
      run: { strategy: "fixture", providers: [], seconds: 0.1, external_calls: 0, cost_eur: 0, accounting_complete: true },
    } });
  });
  await page.goto("/revision");
  await expect(page.getByRole("listbox", { name: "Campos por revisar" }).getByRole("option").first()).toBeVisible();
  await page.keyboard.press("j");
  await page.getByRole("button", { name: "Copiloto", exact: true }).click();
  await page.getByRole("textbox", { name: "Tu pregunta" }).pressSequentially("Antes de aceptar, explica la fuente");
  await page.getByRole("button", { name: "Preguntar", exact: true }).click();
  await expect(page.getByTestId("copilot-answer")).toContainText("Respuesta de prueba de interfaz");
  await page.getByText("Original de prueba", { exact: false }).click();
  await expect(page.getByText("DIAMETER = 2000 mm", { exact: true })).toBeVisible();
  await expect(page.getByText("Original verificado por SHA-256", { exact: true })).toBeVisible();
  expect(await (await request.get(`${base}/equipment/V-101/revisions/A`)).json()).toEqual(before);
});

test("un modelo no disponible muestra el error y no sustituye la respuesta por reglas", async ({ page }) => {
  await page.route("**/copiloto", route => route.fulfill({ status: 503, json: { detail: "Modelo local no disponible para esta prueba" } }));
  await page.goto("/revision");
  await expect(page.getByRole("listbox", { name: "Campos por revisar" }).getByRole("option").first()).toBeVisible();
  await page.keyboard.press("j");
  await page.getByRole("button", { name: "Copiloto", exact: true }).click();
  await page.getByRole("textbox", { name: "Tu pregunta" }).fill("Explica la fuente");
  await page.getByRole("button", { name: "Preguntar", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Copiloto de revisión" }).getByRole("alert")).toContainText("Modelo local no disponible");
  await expect(page.getByText("Qué pasa si está mal", { exact: true })).toHaveCount(0);
});
