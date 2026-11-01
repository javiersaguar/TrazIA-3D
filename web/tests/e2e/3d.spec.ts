import { expect, test } from "@playwright/test";
import { flattenRevision } from "../../src/lib/mock/fields";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve } from "node:path";

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
  await viewer.getByRole("button", { name: "Pausar giro de cámara 360°", exact: true }).nth(1).click();
  await expect(viewer.getByRole("button", { name: "Activar giro de cámara 360°", exact: true })).toHaveCount(2);
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


test("la cámara gira alrededor del equipo y permite detener el giro", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/lab/showcase");
  const canvas = page.locator("canvas");
  await expect(canvas).toHaveAttribute("data-camera-position", /,/);
  const family = await page.locator("[data-equipment-kind]").getAttribute("data-equipment-kind");
  const before = await canvas.getAttribute("data-camera-position");
  await expect.poll(() => canvas.getAttribute("data-camera-position")).not.toBe(before);
  await page.getByRole("button", { name: "Pausar giro de cámara 360°", exact: true }).click();
  await expect(page.locator("[data-equipment-kind]")).toHaveAttribute("data-equipment-kind", family!);
  await page.waitForTimeout(600);
  const paused = await canvas.getAttribute("data-camera-position");
  await page.waitForTimeout(500);
  expect(await canvas.getAttribute("data-camera-position")).toBe(paused);
  await page.getByRole("button", { name: "Activar giro de cámara 360°", exact: true }).click();
  await expect.poll(() => canvas.getAttribute("data-camera-position")).not.toBe(paused);
});

test("movimiento reducido mantiene la cámara estática", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/lab/showcase");
  await expect(page.getByRole("button", { name: "Activar giro de cámara 360°", exact: true })).toBeDisabled();
  const canvas = page.locator("canvas");
  await expect(canvas).toHaveAttribute("data-camera-position", /,/);
  await page.waitForTimeout(500);
  const before = await canvas.getAttribute("data-camera-position");
  await page.waitForTimeout(500);
  expect(await canvas.getAttribute("data-camera-position")).toBe(before);
});

test("el holograma IFC con tres recortes cumple el presupuesto de triángulos", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/lab/holograma");
  await page.getByRole("button", { name: "ifc", exact: true }).click();
  await page.getByRole("slider", { name: "Progreso de materialización" }).fill("100");
  await expect(page.getByText("Brida de boquilla · IFC", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Medir 5 s", exact: true }).click();
  const output = page.getByTestId("hologram-performance");
  await expect(output).toContainText('"triangles"', { timeout: 20000 });
  const measurement = JSON.parse((await output.textContent())!);
  expect(measurement.triangles).toBeGreaterThan(0);
  expect(measurement.triangles).toBeLessThanOrEqual(200000);
});

test("el visor conserva vistas, consulta cotas y descarga el PNG compuesto", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/lab/3d");
  const viewer = page.getByTestId("ifc-viewer");
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30000 });
  const dimension = viewer.getByRole("button", { name: /Longitud de virola:.*Ver fuente/ });
  await expect(dimension).toBeVisible();
  await dimension.focus();
  await expect(dimension).toContainText("Confianza:");
  await expect(dimension).toContainText("GA-V101");
  await viewer.getByRole("button", { name: "Corte", exact: true }).click();
  await viewer.getByRole("slider", { name: "Altura del plano de corte" }).fill("0.4");
  await expect(viewer.getByRole("button", { name: "Corte", exact: true })).toHaveAttribute("aria-pressed", "true");
  await viewer.getByRole("button", { name: "Alzado", exact: true }).click();
  const canvas = viewer.locator("canvas");
  const horizontalOffset = async () => {
    const p = (await canvas.getAttribute("data-camera-position"))!.split(",").map(Number);
    const target = (await canvas.getAttribute("data-camera-target"))!.split(",").map(Number);
    return Math.abs(p[0]! - target[0]!);
  };
  await expect.poll(horizontalOffset).toBeLessThan(.01);
  await viewer.getByRole("textbox", { name: "Nombre de la vista" }).fill("Alzado revisión");
  await viewer.getByRole("button", { name: "Guardar vista", exact: true }).click();
  await page.reload();
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30000 });
  await viewer.getByRole("combobox", { name: "Recuperar vista guardada" }).selectOption({ label: "Alzado revisión" });
  await expect(viewer.getByRole("button", { name: "Iso", exact: true })).toHaveAttribute("aria-pressed", "false");
  await expect(canvas).toHaveAttribute("data-camera-position", /,/);
  await expect.poll(horizontalOffset).toBeLessThan(.01);
  const downloaded = page.waitForEvent("download");
  await viewer.getByRole("button", { name: "Capturar PNG", exact: true }).click();
  const png = await downloaded;
  expect(png.suggestedFilename()).toBe("trazia-ifc.png");
  const bytes = await readFile((await png.path())!);
  expect(bytes.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
  expect(bytes.length).toBeGreaterThan(1000);
  await png.saveAs("../docs/capturas/visor-exportado-01nov.png");
  await page.screenshot({ path: "../docs/capturas/visor-mejoras-01nov.png", fullPage: true });
});

test("la captura BCF conectada empaqueta la cámara y la selección del visor", async ({ page }) => {
  test.skip(!process.env.NEXT_PUBLIC_API_URL, "Conversión BCF mediante la API");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/lab/3d");
  const viewer = page.getByTestId("ifc-viewer");
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30000 });
  const downloaded = page.waitForEvent("download");
  await viewer.getByRole("button", { name: "Captura BCF", exact: true }).click();
  const bcf = await downloaded;
  expect(bcf.suggestedFilename()).toBe("vista_DRAFT.bcfzip");
  const bytes = await readFile((await bcf.path())!);
  expect(bytes.subarray(0, 2).toString()).toBe("PK");
});


test("Revisión cruza marcas por documento, enfoca la página y vuelve al campo", async ({ page }) => {
  test.skip(!process.env.NEXT_PUBLIC_API_URL, "Las marcas se leen contra originales de la API");
  await page.emulateMedia({ reducedMotion: "reduce" });
  const mark = { id: "synthetic-test-cloud", document_id: "OTHER", kind: "cloud", page: 2,
    bbox: [.2, .2, .4, .4], label: null, method: "vector", candidate: true };
  await page.route(/\/diff\?.*marks=true/, route => route.fulfill({ json: {
    layers: { revision_marks: { status: "partial", coordinate_frame: "after-page", is_design_validation: false,
      documents: [{ document_id: "GA-V101", filename: "GAD_V-101_revB.pdf", status: "sin_marcas", marks: [], unread_pages: [] },
        { document_id: "OTHER", filename: "synthetic-other.pdf", status: "parcial", marks: [mark], unread_pages: [1] }],
      unmarked_changes: [{ path: "height", document_id: "GA-V101" }], marks_without_change: [mark], unlocated_changes: [],
    } },
  } }));
  await page.route(/documents\/OTHER/, route => route.fulfill({ contentType: "application/pdf", body: twoPagePdf() }));
  await page.goto("/revision");
  await page.getByRole("radio", { name: "rev B", exact: true }).click();
  const panel = page.getByTestId("revision-mark-checks");
  await expect(panel).toContainText("2 discrepancias");
  await panel.locator("summary").click();
  await expect(panel).toContainText("Sin lectura de marcas en páginas 1");
  await panel.getByRole("button", { name: "height · GA-V101", exact: true }).click();
  await expect(page.getByRole("listbox", { name: "Campos por revisar" }).getByRole("option", { selected: true })).toContainText("Longitud");
  await panel.getByRole("button", { name: "Nube · OTHER, página 2", exact: true }).click();
  await expect(page.getByTestId("pdf-panel")).toHaveAttribute("data-pdf-page", "2");
  await expect(page.getByRole("button", { name: "Marca candidata nube · página 2", exact: true })).toBeVisible();
  await expect(page.getByTestId("pdf-panel")).toContainText("OTHER");
  await page.getByRole("listbox", { name: "Campos por revisar" }).getByRole("option", { selected: true }).click();
  await expect(page.getByTestId("pdf-panel")).toContainText("GA-V101");
  await expect(page.getByTestId("pdf-panel")).toHaveAttribute("data-pdf-page", "1");
});

// Comprobación D.4 opcional: reproducir exactamente el archivo abierto en los visores de escritorio.
if (process.env.PW_IFC_INTEROP) {
  test("D.4 captura el IFC compartido en el visor web @interop", async ({ page }) => {
    const path = process.env.PW_IFC_INTEROP!;
    const body = await readFile(path);
    expect(body.includes(Buffer.from("'synthetic'"))).toBe(true);
    let requests = 0;
    let deliver!: () => void;
    const gate = new Promise<void>(done => { deliver = done; });
    await page.route(/\/(?:demo\/ifc\/rev_b\.ifc|revisions\/(?:B|[^/?]*%3AB)\/ifc)(?:\?|$)/i, async route => {
      requests++;
      await gate;
      await route.fulfill({ contentType: "application/x-step", body });
    });
    await page.emulateMedia({ reducedMotion: "reduce", colorScheme: "dark" });
    await page.goto("/revision");
    await page.getByRole("radio", { name: "rev B", exact: true }).click();
    const viewer = page.getByTestId("ifc-viewer");
    try {
      await expect(viewer).toHaveAttribute("data-phase", "loading");
    } finally {
      deliver();
    }
    await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30000 });
    await expect.poll(() => requests).toBeGreaterThan(0);
    expect(Number(await viewer.getAttribute("data-products"))).toBeGreaterThan(0);
    const directory = resolve("../docs/ifc-checks/01nov");
    await mkdir(directory, { recursive: true });
    await page.screenshot({ path: resolve(directory, "web-ifc.png"), fullPage: true });
    await writeFile(resolve(directory, "web-ifc.json"), JSON.stringify({
      at: new Date().toISOString(), synthetic: true, draft: true,
      input_sha256: createHash("sha256").update(body).digest("hex"), bytes: body.length,
      products: Number(await viewer.getAttribute("data-products")),
      triangles: Number(await viewer.getAttribute("data-triangles")),
      delivery: "Playwright sirve los bytes del IFC indicado; no modifica su geometría",
      renderer: process.env.PW_CPU_ONLY === "1" ? "SwiftShader CPU" : "navegador",
    }, null, 2) + "\n");
  });
}
