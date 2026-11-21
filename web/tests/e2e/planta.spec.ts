import { expect, test, type Locator } from "@playwright/test";

/*
  Encuadre por selección en los escenarios de proceso (contrato C2): al elegir un equipo la cámara
  queda en perspectiva, elevada, mirando a su caja y a una distancia proporcionada a su tamaño;
  Esc vuelve a la vista general.
*/

type Vec = [number, number, number];
const vector = (raw: string | null): Vec => (raw ?? "").split(",").map(Number) as Vec;

async function pose(viewer: Locator) {
  const canvas = viewer.locator("canvas");
  const eye = vector(await canvas.getAttribute("data-camera-position"));
  const target = vector(await canvas.getAttribute("data-camera-target"));
  const [dx, dy, dz] = [eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]];
  return {
    eye,
    target,
    distance: Math.hypot(dx, dy, dz),
    elevation: (Math.atan2(dy, Math.hypot(dx, dz)) * 180) / Math.PI,
  };
}

/** Espera a que la cámara deje de moverse y devuelve su pose. */
async function settled(viewer: Locator) {
  let previous = await pose(viewer);
  for (let i = 0; i < 40; i++) {
    await viewer.page().waitForTimeout(150);
    const current = await pose(viewer);
    if (current.eye.every((v, k) => Math.abs(v - previous.eye[k]!) < 1e-3)) return current;
    previous = current;
  }
  return previous;
}

test("al elegir P-150 la cámara lo encuadra en perspectiva y Esc vuelve a la vista general", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/proyectos-proceso/plataforma-marina");
  const viewer = page.getByTestId("ifc-viewer");
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30_000 });
  const canvas = viewer.locator("canvas");
  await expect(canvas).toHaveAttribute("data-camera-projection", "perspective");
  const general = await settled(viewer);
  expect(general.elevation).toBeGreaterThan(10);

  await page.locator("tbody th button", { hasText: "P-150" }).first().click();
  await expect(viewer).toHaveAttribute("data-selection", "element:P-150");
  await expect(viewer).toHaveAttribute("data-selection-bounds", /.+/);
  await expect.poll(async () => (await pose(viewer)).distance, { timeout: 10_000 }).toBeLessThan(general.distance * 0.5);
  const shot = await settled(viewer);
  const bounds = (await viewer.getAttribute("data-selection-bounds"))!.split(",").map(Number);
  const [min, max] = [bounds.slice(0, 3), bounds.slice(3, 6)];
  const diagonal = Math.hypot(max[0]! - min[0]!, max[1]! - min[1]!, max[2]! - min[2]!);

  expect(shot.elevation).toBeGreaterThanOrEqual(15);
  expect(shot.elevation).toBeLessThanOrEqual(65);
  shot.target.forEach((value, axis) => {
    expect(value).toBeGreaterThanOrEqual(min[axis]! - 0.05);
    expect(value).toBeLessThanOrEqual(max[axis]! + 0.05);
  });
  expect(shot.distance / diagonal).toBeGreaterThan(1);
  expect(shot.distance / diagonal).toBeLessThan(4);
  await expect(canvas).toHaveAttribute("data-camera-projection", "perspective");
  // Objetivo de rendimiento del encuadre (muestreo + rayos BVH + oclusión): < 40 ms.
  expect(Number(await viewer.getAttribute("data-framing-ms"))).toBeLessThan(40);

  await page.keyboard.press("Escape");
  await expect(viewer).toHaveAttribute("data-selection", "");
  await expect.poll(async () => (await pose(viewer)).distance, { timeout: 10_000 }).toBeGreaterThan(general.distance * 0.9);
  const back = await settled(viewer);
  back.eye.forEach((value, axis) => expect(value).toBeCloseTo(general.eye[axis]!, 0));
  await expect(canvas).toHaveAttribute("data-camera-projection", "perspective");
});

test("Alzado y Planta fuerzan la ortográfica y Perspectiva alterna la vista general", async ({ page }) => {
  await page.goto("/proyectos-proceso/plataforma-marina");
  const viewer = page.getByTestId("ifc-viewer");
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30_000 });
  const canvas = viewer.locator("canvas");
  await expect(canvas).toHaveAttribute("data-camera-projection", "perspective");
  await viewer.getByRole("button", { name: "Alzado" }).click();
  await expect(canvas).toHaveAttribute("data-camera-projection", "orthographic");
  await viewer.getByRole("button", { name: "Planta" }).click();
  await expect(canvas).toHaveAttribute("data-camera-projection", "orthographic");
  await viewer.getByRole("button", { name: "General" }).click();
  await expect(canvas).toHaveAttribute("data-camera-projection", "perspective");
  const toggle = viewer.getByRole("button", { name: "Perspectiva" });
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await toggle.click();
  await expect(canvas).toHaveAttribute("data-camera-projection", "orthographic");
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
});

test("la ficha abre una pieza, muestra sus cotas y genera un borrador IFC", async ({ page }) => {
  test.skip(!process.env.NEXT_PUBLIC_API_URL, "La generación paramétrica necesita API");
  test.setTimeout(95_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/proyectos-proceso/plataforma-marina");
  const viewer = page.getByTestId("ifc-viewer");
  const sheet = page.getByRole("region", { name: "Ficha de componente" });
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30_000 });
  await sheet.getByRole("button", { name: /^V-110 ·/ }).click();
  await expect(sheet.getByRole("heading", { name: "Envolvente IFC" })).toBeVisible();
  await sheet.getByRole("list", { name: "Piezas del conjunto" }).getByRole("button", { name: "Virola", exact: true }).click();
  await expect(viewer).toHaveAttribute("data-selection", "detail:element:V-110/virola");
  await sheet.getByRole("button", { name: "Cotas en 3D" }).click();
  await expect(sheet.getByRole("button", { name: "Cotas en 3D" })).toHaveAttribute("aria-pressed", "true");
  await sheet.getByRole("button", { name: "Al conjunto" }).click();
  await sheet.getByLabel(/Ancho o diámetro/).fill("3.8");
  await sheet.getByRole("button", { name: "Previsualizar borrador" }).click();
  await expect(viewer).toHaveAttribute("data-ifc-url", /^blob:/, { timeout: 45_000 });
  await expect(sheet.getByText("Actual 3,8", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Descargar IFC", exact: true })).toHaveAttribute("download", "SIM-MAR-ENSAYO-DRAFT.ifc");
  await sheet.getByRole("button", { name: "Descartar borrador" }).click();
  await expect(viewer).toHaveAttribute("data-ifc-url", /SIM-MAR-A\.ifc$/);
});

test("sin API la ficha escala el equipo en el navegador y avisa de las líneas que revisar", async ({ page }) => {
  test.skip(!!process.env.NEXT_PUBLIC_API_URL, "Con API el borrador lo genera el servidor");
  test.setTimeout(95_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/proyectos-proceso/plataforma-marina");
  const viewer = page.getByTestId("ifc-viewer");
  const sheet = page.getByRole("region", { name: "Ficha de componente" });
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30_000 });
  await sheet.getByRole("button", { name: /^V-110 ·/ }).click();
  await expect(sheet.getByText(/navegador escala la geometría IFC/)).toBeVisible();
  await sheet.getByLabel(/Largo nominal/).fill("9.9");
  await sheet.getByRole("button", { name: "Previsualizar borrador" }).click();
  await expect(viewer).toHaveAttribute("data-ifc-url", /^blob:/, { timeout: 45_000 });
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 30_000 });
  await expect(sheet.getByText("Actual 9,9", { exact: true })).toBeVisible();
  await expect(sheet.getByText(/Revisar conexiones: .*OL-05/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Descargar IFC", exact: true })).toHaveAttribute("download", "SIM-MAR-ENSAYO-DRAFT.ifc");
  await sheet.getByRole("button", { name: "Descartar borrador" }).click();
  await expect(viewer).toHaveAttribute("data-ifc-url", /SIM-MAR-A\.ifc$/);
});