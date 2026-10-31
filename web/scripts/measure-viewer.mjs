// Servidor ya levantado; solo escenas públicas sintéticas.
import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const output = fileURLToPath(new URL("../../generated/visor-31/", import.meta.url));
const captures = fileURLToPath(new URL("../../docs/capturas/", import.meta.url));
await mkdir(output, { recursive: true });
await mkdir(captures, { recursive: true });
const browser = await chromium.launch({ channel: process.env.PW_CHANNEL ?? "chrome", headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 }, reducedMotion: "no-preference" });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem("theme", "dark");
    sessionStorage.setItem("trazia.intro", "visto");
  });
  const base = process.env.PREVIEW_URL ?? "http://localhost:3120";
  await page.goto(`${base}/lab/holograma`);
  await page.getByRole("button", { name: "ifc", exact: true }).click();
  await page.getByText("Brida de boquilla · IFC", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Medir 5 s", exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-testid="hologram-performance"]')?.textContent.includes('"triangles"'));
  const measurement = JSON.parse(await page.getByTestId("hologram-performance").textContent());
  if (measurement.triangles > 200000) throw new Error("Se supera el presupuesto de triángulos");
  await writeFile(`${output}/rendimiento.json`, JSON.stringify({ at: new Date().toISOString(), ...measurement }, null, 2));
  await page.getByRole("button", { name: "Pausar giro de cámara 360°", exact: true }).click();
  await page.screenshot({ path: `${captures}/31oct-holograma-ifc.png` });

  if (process.argv.includes("--orbita-completa")) {
    await page.goto(`${base}/lab/showcase`);
    await page.waitForFunction(() => document.querySelector("canvas")?.getAttribute("data-camera-target"));
    const pose = () => page.locator("canvas").evaluate(canvas => ({
      eye: canvas.getAttribute("data-camera-position").split(",").map(Number),
      target: canvas.getAttribute("data-camera-target").split(",").map(Number),
    }));
    const angle = value => Math.atan2(value.eye[0] - value.target[0], value.eye[2] - value.target[2]);
    const radius = value => Math.hypot(...value.eye.map((v, i) => v - value.target[i]));
    let previous = await pose();
    const initialRadius = radius(previous), start = Date.now();
    let sum = 0, maxRadiusError = 0;
    while (Date.now() - start < 64000) {
      await page.waitForTimeout(250);
      const next = await pose();
      let delta = angle(next) - angle(previous);
      if (delta > Math.PI) delta -= Math.PI * 2;
      if (delta < -Math.PI) delta += Math.PI * 2;
      sum += delta;
      maxRadiusError = Math.max(maxRadiusError, Math.abs(radius(next) - initialRadius));
      previous = next;
    }
    const orbit = { at: new Date().toISOString(), seconds: (Date.now() - start) / 1000, degrees: sum * 180 / Math.PI, maxRadiusError };
    await writeFile(`${output}/orbita.json`, JSON.stringify(orbit, null, 2));
    if (orbit.degrees < 360 || maxRadiusError > 0.001) throw new Error("No completa una órbita estable");
  }

  for (const [route, ready] of [["revision", "ifc-viewer"], ["cambios", "revision-morph"], ["modelo", null]]) {
    await page.goto(`${base}/${route}`);
    if (ready) await page.getByTestId(ready).locator("canvas").waitFor();
    else await page.locator('[data-source="ifc"] canvas').first().waitFor();
    if (route === "modelo") await page.getByRole("slider", { name: "Progreso de materialización", exact: true }).fill("100");
    await page.getByRole("button", { name: "Pausar giro de cámara 360°", exact: true }).first().click();
    await page.waitForTimeout(750);
    await page.screenshot({ path: `${captures}/31oct-${route}.png` });
  }
  if (errors.length) throw new Error(errors.join("\n"));
  console.log(JSON.stringify(measurement));
} finally {
  await browser.close();
}
