import { expect, test } from "@playwright/test";
import { flattenRevision } from "../../src/lib/mock/fields";

// Dos páginas sintéticas en memoria para verificar la navegación PDF sin originales privados.
function twoPagePdf() {
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 500] /Contents 5 0 R >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 500] /Contents 6 0 R >>",
    "<< /Length 0 >>\nstream\n\nendstream",
    "<< /Length 0 >>\nstream\n\nendstream",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((o, i) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 7\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((n) => String(n).padStart(10, "0") + " 00000 n ")
    .join(
      "\n",
    )}\ntrailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(pdf);
}

test("el holograma IFC permite scrub y respeta movimiento reducido", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/lab/holograma");
  await page.getByRole("button", { name: "ifc", exact: true }).click();
  await expect(page.getByRole("slider")).toBeEnabled({ timeout: 30000 });
  await page.getByRole("slider").fill("50");
  await expect(page.locator("output").first()).toHaveText("50 %");
  await expect(
    page.getByText("Geometría leída de rev_b.ifc · datos sintéticos"),
  ).toBeVisible();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.reload();
  await page.getByRole("button", { name: "ifc", exact: true }).click();
  await expect(page.locator("output").first()).toHaveText("100 %", {
    timeout: 30000,
  });
  await expect(page.getByRole("slider")).toBeDisabled();
  expect(errors).toEqual([]);
});

test("Cambios conserva extremos exactos, segmentos y comparación A B", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/cambios");
  const viewer = page.getByTestId("revision-morph");
  await expect(viewer).toHaveAttribute("data-phase", "ready", {
    timeout: 30000,
  });
  const range = page.getByRole("slider", {
    name: "Interpolación IFC de A a B",
  });
  await range.fill("1");
  await expect(viewer).toHaveAttribute("data-progress", "1.000");
  await expect(
    page.getByText("IFC B exacto · sintético", { exact: true }),
  ).toBeVisible();
  await range.fill("0");
  await expect(viewer).toHaveAttribute("data-progress", "0.000");
  await page
    .getByRole("button", { name: "Solo modificados", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Solo modificados", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("combobox", { name: "Velocidad de los cambios" })
    .selectOption("2");
  await page
    .getByRole("button", { name: "Reproducir los cambios", exact: true })
    .click();
  await expect(page.getByText(/Paso 1 de/)).toBeVisible();
  await page.getByText("A | B", { exact: true }).click();
  await expect(viewer.locator("canvas")).toHaveCount(2);
  await page.getByRole("button", { name: "Presentación", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Salir de presentación" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Presentación", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("Revisión enlaza evidencias, inspecciona IFC y recuerda tamaños", async ({
  page,
}) => {
  await page.goto("/revision");
  await expect(page.getByTestId("ifc-viewer")).toHaveAttribute(
    "data-phase",
    "ready",
    { timeout: 30000 },
  );
  const queue = page.getByRole("listbox", { name: "Campos por revisar" });
  await expect(queue.getByRole("option").first()).toBeVisible();
  await page.keyboard.press("j");
  await page
    .getByRole("button", { name: "Inspector IFC", exact: true })
    .click();
  await expect(page.getByTestId("inspector-guid")).not.toBeEmpty();
  const separator = page.getByRole("separator").first();
  const before = Number(await separator.getAttribute("aria-valuenow"));
  await separator.focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  const resized = Number(await separator.getAttribute("aria-valuenow"));
  expect(resized).toBeGreaterThan(before);
  await page.reload();
  await expect(page.getByRole("separator").first()).toHaveAttribute(
    "aria-valuenow",
    String(resized),
  );
  await page.getByText("Modelo", { exact: true }).click();
  await expect(page.locator('[data-panel][id="pdf"]')).toHaveCSS(
    "flex-grow",
    "0",
  );
});

test("PDF muestra miniaturas y cambia a la segunda página", async ({
  page,
}) => {
  await page.route(/(?:GAD_V-101_revA\.pdf|documents\/GA-V101)/, (route) =>
    route.fulfill({ contentType: "application/pdf", body: twoPagePdf() }),
  );
  await page.goto("/revision");
  await expect(page.getByRole("button", { name: "Ver página 2" })).toBeVisible({
    timeout: 30000,
  });
  await page.getByRole("button", { name: "Ver página 2" }).click();
  await expect(page.getByTestId("pdf-panel")).toHaveAttribute(
    "data-pdf-page",
    "2",
  );
});

test("la aprobación API recupera un conflicto y guarda la huella con If-Match", async ({
  page,
  request,
}) => {
  test.skip(
    !process.env.NEXT_PUBLIC_API_URL,
    "La aprobación requiere la API aislada de pruebas",
  );
  const base = process.env.NEXT_PUBLIC_API_URL!;
  const initial = await request.get(`${base}/equipment/V-101/revisions/B`);
  expect(initial.ok()).toBeTruthy();
  const revision = await initial.json(),
    identity = `${revision.project_id}:${revision.equipment.id}:${revision.revision}`;
  let etag = initial.headers().etag;
  for (const field of flattenRevision(revision)) {
    const response = await request.patch(
      `${base}/revisions/${encodeURIComponent(identity)}/fields/${encodeURIComponent(field.path)}`,
      {
        headers: { "If-Match": etag!, "Idempotency-Key": crypto.randomUUID() },
        data: { state: "accepted", actor: "Prueba de revisión sintética" },
      },
    );
    expect(response.ok()).toBeTruthy();
    etag = response.headers().etag;
  }
  await page.goto("/revision");
  await page.getByText("rev B", { exact: true }).click();
  const approve = page.getByRole("button", {
    name: "Aprobar revisión",
    exact: true,
  });
  await expect(approve).toBeEnabled({ timeout: 30000 });
  await page.route(
    "**/approve",
    (route) =>
      route.fulfill({
        status: 412,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Versión desactualizada" }),
      }),
    { times: 1 },
  );
  await approve.click();
  await page
    .getByRole("textbox", { name: "Nombre del revisor" })
    .fill("Revisor de prueba sintética");
  await page
    .getByRole("button", { name: "Guardar aprobación", exact: true })
    .click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "La revisión cambió",
  );
  await page
    .getByRole("button", { name: "Recargar campos", exact: true })
    .click();
  await approve.click();
  const saved = page.waitForResponse(
    (r) => r.url().endsWith("/approve") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Guardar aprobación", exact: true })
    .click();
  const response = await saved;
  expect(response.ok()).toBeTruthy();
  expect(response.request().headers()["if-match"]).toBe(etag);
  const body = await response.json();
  expect(body.approval.reviewer).toBe("Revisor de prueba sintética");
  expect(body.approval.input_sha256).toMatch(/^[a-f0-9]{64}$/);
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page
    .getByRole("listbox", { name: "Campos por revisar" })
    .getByRole("option")
    .first()
    .click();
  await page
    .getByRole("button", { name: "Inspector IFC", exact: true })
    .click();
  await expect(page.getByTestId("inspector-guid")).not.toBeEmpty();
  await page.screenshot({
    path: "../docs/capturas/agente2-25-revision-api.png",
    fullPage: true,
  });
});

test("una brida IFC conserva su GUID y selecciona la evidencia de su boquilla", async ({
  page,
}) => {
  await page.goto("/revision");
  await expect(page.getByTestId("ifc-viewer")).toHaveAttribute(
    "data-products",
    "73",
    { timeout: 30000 },
  );
  await page.getByRole("button", { name: "Elementos", exact: true }).click();
  await page
    .getByRole("button", { name: "Brida · Boquilla N1", exact: true })
    .click();
  await expect(
    page
      .getByRole("listbox", { name: "Campos por revisar" })
      .getByRole("option", { selected: true }),
  ).toContainText("N1");
  await page
    .getByRole("button", { name: "Inspector IFC", exact: true })
    .click();
  await expect(page.getByTestId("inspector-guid")).not.toBeEmpty();
  await expect(page.getByTestId("derived-origin")).toContainText(
    "no leído del plano",
  );
});

test("la portada carga el 3D por separado y el clic cambia la familia", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  await page.addInitScript(() =>
    sessionStorage.setItem("trazia.intro", "visto"),
  );
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const vessel = page.locator("[data-equipment-kind]").first();
  await expect(vessel).toBeVisible({ timeout: 30000 });
  await expect(vessel.locator("canvas")).toBeVisible();
  const kind = await vessel.getAttribute("data-equipment-kind");
  await vessel.locator("canvas").click({ position: { x: 20, y: 200 } });
  await expect(vessel).not.toHaveAttribute("data-equipment-kind", kind!);
  expect(errors).toEqual([]);
});

test("el seguimiento de cambios conserva el acercamiento al cambiar la narración", async ({
  page,
}) => {
  await page.goto("/cambios");
  const viewer = page.getByTestId("revision-morph");
  await expect(viewer).toHaveAttribute("data-phase", "ready", {
    timeout: 30000,
  });
  const canvas = viewer.locator("canvas");
  await expect
    .poll(async () => Number(await canvas.getAttribute("data-camera-zoom")))
    .toBeGreaterThan(0);
  const initial = Number(await canvas.getAttribute("data-camera-zoom"));
  await page
    .getByRole("button", { name: "Reproducir los cambios", exact: true })
    .click();
  await expect
    .poll(async () => Number(await canvas.getAttribute("data-camera-zoom")), {
      timeout: 5000,
    })
    .toBeGreaterThan(initial * 2);
});
