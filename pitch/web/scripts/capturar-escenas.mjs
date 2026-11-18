// Captura cada escena del pitch a 1920×1080 y guarda sus notas para montar el PowerPoint.
// Uso: node scripts/capturar-escenas.mjs <url> <carpeta>. Lo lanza scripts/exportar_pptx.py.
import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { join } from "node:path";

import { pitch, scenes } from "../src/pitch-data.js";

// Playwright ya está instalado para las pruebas de la web; no se añade otra dependencia al pitch.
const require = createRequire(new URL("../../../web/package.json", import.meta.url));
const { chromium } = require("@playwright/test");

const [url = "http://127.0.0.1:4179/", carpeta = "escenas"] = process.argv.slice(2);
const ESPERA_MS = 5200; // entrada de la escena, clips y cifras animadas

await mkdir(carpeta, { recursive: true });
const browser = await chromium.launch({ channel: process.env.PW_CHANNEL ?? "chrome" });
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto(url, { waitUntil: "networkidle" });
  // Cronómetro y botón de notas son herramientas de quien presenta, no contenido de la diapositiva.
  await page.addStyleTag({ content: ".presentation-tools > :not(.dataset) { visibility: hidden !important; }" });
  const salida = [];
  for (const [index, scene] of scenes.entries()) {
    if (index > 0) await page.keyboard.press("ArrowRight");
    await page.waitForFunction((n) => document.querySelector(".deck-stage")?.dataset.sceneIndex === String(n), index + 1);
    await page.waitForTimeout(ESPERA_MS);
    const archivo = `${String(index + 1).padStart(2, "0")}-${scene.id}.png`;
    await page.screenshot({ path: join(carpeta, archivo) });
    salida.push({ archivo, id: scene.id, titulo: [scene.title, scene.accent].filter(Boolean).join(" "),
      segundos: scene.seconds, notas: scene.notes });
    console.log(`${archivo} · ${scene.seconds} s`);
  }
  await writeFile(join(carpeta, "escenas.json"),
    JSON.stringify({ titulo: `${pitch.brand} · ${pitch.challenge}`, escenas: salida }, null, 1) + "\n");
} finally {
  await browser.close();
}
