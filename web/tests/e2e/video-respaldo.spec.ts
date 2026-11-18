import { test, type CDPSession, type Locator, type Page } from "@playwright/test";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

/*
  Vídeo de respaldo de la demo (ROADMAP 4.6): recorre la app en el orden de docs/GUION_DEMO.md,
  con un cursor visible y un rótulo por pantalla, porque el vídeo va sin voz.
  Graba con el screencast de Chrome (JPEG de calidad 90) en lugar del vídeo de Playwright,
  limitado a 1 Mbit/s, para que los textos se lean a 1080p.
  No se lanza a mano: scripts/video_respaldo.py compila la web, ejecuta este proyecto y monta el MP4.
*/
const FOTOGRAMAS = process.env.VIDEO_FRAMES ?? resolve(__dirname, "../../../generated/video-respaldo/fotogramas");
const EJEMPLOS = resolve(__dirname, "../../../examples/documents");

test.use({ viewport: { width: 1920, height: 1080 }, colorScheme: "dark" });
test.setTimeout(8 * 60_000);

class Grabadora {
  private sesion: CDPSession | null = null;
  readonly fotogramas: { archivo: string; t: number }[] = [];

  async empezar(page: Page) {
    rmSync(FOTOGRAMAS, { recursive: true, force: true });
    mkdirSync(FOTOGRAMAS, { recursive: true });
    this.sesion = await page.context().newCDPSession(page);
    this.sesion.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
      const archivo = `${String(this.fotogramas.length).padStart(6, "0")}.jpg`;
      writeFileSync(join(FOTOGRAMAS, archivo), Buffer.from(data, "base64"));
      this.fotogramas.push({ archivo, t: metadata.timestamp ?? Date.now() / 1000 });
      void this.sesion?.send("Page.screencastFrameAck", { sessionId }).catch(() => undefined);
    });
    await this.sesion.send("Page.startScreencast", { format: "jpeg", quality: 90, maxWidth: 1920, maxHeight: 1080 });
  }

  /** Lista para el demuxer concat de ffmpeg: cada fotograma dura hasta que llega el siguiente. */
  async terminar() {
    await this.sesion?.send("Page.stopScreencast").catch(() => undefined);
    const lineas = ["ffconcat version 1.0"];
    this.fotogramas.forEach(({ archivo, t }, i) => {
      const siguiente = this.fotogramas[i + 1]?.t ?? t + 2;
      lineas.push(`file ${archivo}`, `duration ${Math.max(0.001, siguiente - t).toFixed(4)}`);
    });
    const ultimo = this.fotogramas.at(-1);
    if (ultimo) lineas.push(`file ${ultimo.archivo}`); // el demuxer ignora la duración del último
    writeFileSync(join(FOTOGRAMAS, "fotogramas.txt"), lineas.join("\n") + "\n");
    console.log(`[vídeo] ${this.fotogramas.length} fotogramas en ${FOTOGRAMAS}`);
  }
}

/** Cursor, rótulo y sin la insignia de `next dev`. Idempotente: se llama tras cada navegación. */
async function preparar(page: Page) {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.evaluate(() => {
    document.querySelectorAll("nextjs-portal").forEach((nodo) => nodo.remove());
    if (document.getElementById("__cursor")) return;
    const cursor = document.createElement("div");
    cursor.id = "__cursor";
    Object.assign(cursor.style, {
      position: "fixed", left: "-60px", top: "-60px", width: "26px", height: "26px", borderRadius: "50%",
      border: "2px solid #fff", background: "rgba(86,182,255,.35)", boxShadow: "0 0 0 1px rgba(0,0,0,.5)",
      transform: "translate(-50%,-50%)", pointerEvents: "none", zIndex: "2147483647",
    });
    const rotulo = document.createElement("div");
    rotulo.id = "__rotulo";
    Object.assign(rotulo.style, {
      position: "fixed", left: "50%", bottom: "32px", transform: "translateX(-50%)", maxWidth: "80vw",
      padding: "12px 22px", borderRadius: "12px", background: "rgba(8,12,18,.88)", color: "#f5f7fa",
      font: "600 22px/1.3 system-ui, sans-serif", border: "1px solid rgba(86,182,255,.45)",
      opacity: "0", transition: "opacity .35s ease", pointerEvents: "none", zIndex: "2147483646",
    });
    document.documentElement.append(cursor, rotulo);
    document.addEventListener("mousemove", (e) => {
      cursor.style.left = `${e.clientX}px`;
      cursor.style.top = `${e.clientY}px`;
    }, true);
    document.addEventListener("mousedown", () => {
      cursor.animate([{ transform: "translate(-50%,-50%) scale(1)" }, { transform: "translate(-50%,-50%) scale(.65)" },
        { transform: "translate(-50%,-50%) scale(1)" }], { duration: 260 });
    }, true);
  });
}

async function rotular(page: Page, texto: string) {
  await page.evaluate((t) => {
    const rotulo = document.getElementById("__rotulo");
    if (!rotulo) return;
    rotulo.textContent = t;
    rotulo.style.opacity = t ? "1" : "0";
  }, texto);
}

let raton = { x: 960, y: 540 };
async function mover(page: Page, x: number, y: number) {
  const pasos = Math.max(12, Math.round(Math.hypot(x - raton.x, y - raton.y) / 22));
  await page.mouse.move(x, y, { steps: pasos });
  raton = { x, y };
}

/** Lleva el cursor al elemento y, si se pide, pulsa. Si el elemento no aparece, sigue el recorrido. */
async function señalar(page: Page, objetivo: Locator, pulsar = true, paso = "") {
  try {
    await objetivo.scrollIntoViewIfNeeded({ timeout: 8_000 });
    const caja = await objetivo.boundingBox({ timeout: 8_000 });
    if (!caja) throw new Error("sin caja");
    await mover(page, caja.x + caja.width / 2, caja.y + caja.height / 2);
    await page.waitForTimeout(350);
    if (pulsar) await page.mouse.click(raton.x, raton.y);
  } catch (error) {
    console.warn(`[vídeo] no se pudo «${paso || objetivo}»: ${(error as Error).message.split("\n")[0]}`);
  }
}

async function intentar(paso: string, accion: () => Promise<unknown>) {
  try {
    await accion();
  } catch (error) {
    console.warn(`[vídeo] no se pudo «${paso}»: ${(error as Error).message.split("\n")[0]}`);
  }
}

async function abrir(page: Page, ruta: string, texto: string) {
  await page.goto(ruta);
  await preparar(page);
  await page.mouse.move(raton.x, raton.y);
  await rotular(page, texto);
}

const visorListo = (page: Page, id = "ifc-viewer") =>
  page.locator(`[data-testid="${id}"][data-phase="ready"]`).first().waitFor({ timeout: 45_000 });

test("vídeo de respaldo de la demo", async ({ page }) => {
  await page.addInitScript(() => {
    try {
      window.localStorage.setItem("theme", "dark");
    } catch {
      /* sin almacenamiento */
    }
  });
  const grabadora = new Grabadora();
  await grabadora.empezar(page);

  // 1 · Entran los documentos
  await abrir(page, "/documentos", "TrazIA-3D · demo grabada con datos sintéticos");
  await page.waitForTimeout(3000);
  await rotular(page, "1 · Entran el plano GA y la hoja de datos del V-101");
  await señalar(page, page.getByLabel("Elegir documentos").locator("xpath=.."), false, "bandeja");
  await intentar("añadir los documentos", () =>
    page.getByLabel("Elegir documentos").setInputFiles([`${EJEMPLOS}/GAD_V-101_revA.pdf`, `${EJEMPLOS}/HDM_V-101_revA.xlsx`]),
  );
  await page.waitForTimeout(6000);

  // 2 · Pipeline D
  await abrir(page, "/pipeline", "2 · La lectura en cascada: documentos, lectura, fusión y modelo");
  await intentar("elegir D", () => page.getByLabel("Estrategia del grafo").selectOption("d_hibrido", { timeout: 15_000 }));
  await page.waitForTimeout(1500);
  await señalar(page, page.getByRole("button", { name: "Reproducir explicación" }), true, "reproducir");
  await page.waitForTimeout(16_000);

  // 3 · Cada dato tiene un origen
  await abrir(page, "/modelo?vista=revision", "3 · Cada valor enlaza con la región del plano de la que sale");
  await intentar("esperar el modelo", () => visorListo(page));
  const cola = page.getByRole("listbox", { name: "Campos por revisar" });
  await page.waitForTimeout(1500);
  await señalar(page, cola.getByRole("option", { name: /Diámetro de la virola/ }).first(), true, "diámetro");
  await page.waitForTimeout(5000);
  await rotular(page, "La cola va por riesgo: primero lo que hay que confirmar");
  await señalar(page, page.getByRole("button", { name: "Por revisar", exact: true }).first(), true, "por revisar");
  await page.waitForTimeout(4000);

  // 4 · Elegimos con datos
  await abrir(page, "/bench?vista=estudio", "4 · Cuatro estrategias medidas con la misma rúbrica · sintéticos, IC 95 %");
  await page.waitForTimeout(5000);
  for (let i = 0; i < 4; i++) {
    await page.mouse.wheel(0, 260);
    await page.waitForTimeout(900);
  }
  await page.waitForTimeout(3000);

  // 5 · Del plano al modelo, en la portada
  await abrir(page, "/", "5 · Del plano al modelo: el plano GA se levanta hasta su IFC");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(4000);
  await intentar("ir a «Del plano al modelo»", async () => {
    const seccion = page.locator("#del-plano");
    const caja = await seccion.boundingBox({ timeout: 8_000 });
    const destino = (caja?.y ?? 1600) + 200;
    for (let recorrido = 0; recorrido < destino; recorrido += 120) {
      await page.mouse.wheel(0, 120);
      await page.waitForTimeout(140);
    }
  });
  for (let i = 0; i < 14; i++) {
    await page.mouse.wheel(0, 110);
    await page.waitForTimeout(260);
  }
  await page.waitForTimeout(3000);

  // 6 · El IFC por dentro
  await abrir(page, "/modelo?vista=revision", "6 · Es el IFC4, no un dibujo aparte: Rayos X, explosionado e inspector");
  await intentar("esperar el modelo", () => visorListo(page));
  await señalar(page, page.getByRole("radio", { name: "Iso", exact: true }).first(), true, "Iso");
  await page.waitForTimeout(2500);
  await señalar(page, page.getByRole("radio", { name: "Rayos X", exact: true }).first(), true, "Rayos X");
  await page.waitForTimeout(3000);
  await señalar(page, page.getByRole("radio", { name: "Explosionado", exact: true }).first(), true, "Explosionado");
  await page.waitForTimeout(3500);
  await señalar(page, page.getByRole("radio", { name: "Rayos X", exact: true }).first(), true, "Rayos X");
  await señalar(page, page.getByRole("listbox", { name: "Campos por revisar" }).getByRole("option", { name: /\bN2\b/ }).first(),
    true, "N2");
  await page.waitForTimeout(5000);

  // 7 · Llega la revisión B
  await abrir(page, "/modelo?vista=cambios", "7 · Llega la revisión B: qué cambió, cuánto y dónde");
  await intentar("esperar el visor", () => visorListo(page, "revision-morph"));
  // Siguiendo el cambio, la cámara entra hasta la pieza y el recipiente sale cortado: vista general
  await señalar(page, page.getByRole("button", { name: "Vista general", exact: true }), true, "vista general");
  await intentar("dejar de seguir el cambio", async () => {
    const seguir = page.getByRole("button", { name: "Seguir el cambio", exact: true });
    if ((await seguir.getAttribute("aria-pressed", { timeout: 5_000 })) === "true") await señalar(page, seguir, true);
  });
  await page.waitForTimeout(2000);
  // Sin foco en un botón, Espacio reproduce los cambios en lugar de pulsar ese botón
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.keyboard.press("Space");
  await page.waitForTimeout(18_000);
  await intentar("pausar", async () => {
    const pausa = page.getByRole("button", { name: "Pausar" }).first();
    if (await pausa.isVisible()) await pausa.click();
  });
  await señalar(page, page.getByText("N4 · boquilla nueva", { exact: true }).first(), true, "N4");
  await intentar("esperar la transición", () => visorListo(page, "revision-morph"));
  await page.waitForTimeout(4000);
  await rotular(page, "Y a quién afecta: impacto por disciplina");
  await señalar(page, page.getByText("Impacto por disciplina").first(), false, "impacto");
  await page.waitForTimeout(5000);

  // 8 · Diseños del catálogo, editables en directo
  await abrir(page, "/modelo?vista=disenos&diseno=BC-AC101", "8 · Cualquier diseño del catálogo: el IFC se regenera al cambiar una medida");
  await intentar("esperar el IFC", () =>
    page.locator('[data-testid="design-ifc-status"][data-state="ready"]').waitFor({ timeout: 45_000 }));
  await page.waitForTimeout(3000);
  await intentar("arrastrar el alto", async () => {
    const alto = page.getByRole("slider", { name: "Alto (deslizador)" });
    await alto.scrollIntoViewIfNeeded();
    const caja = await alto.boundingBox();
    if (!caja) throw new Error("sin caja");
    const valor = Number(await alto.inputValue());
    const [min, max] = [Number(await alto.getAttribute("min")), Number(await alto.getAttribute("max"))];
    const x = caja.x + ((valor - min) / (max - min)) * caja.width;
    await mover(page, x, caja.y + caja.height / 2);
    await page.mouse.down();
    await mover(page, x + caja.width * 0.22, caja.y + caja.height / 2);
    await page.mouse.up();
  });
  await page.waitForTimeout(4000);
  await señalar(page, page.getByRole("button", { name: "Ocultar Colector", exact: true }), true, "ocultar colector");
  await page.waitForTimeout(4500);

  // 9 · Impacto
  await abrir(page, "/impacto", "9 · Impacto: las horas de revisión que se ahorran, con su supuesto a la vista");
  await page.waitForTimeout(7000);
  await rotular(page, "TrazIA-3D · del plano al modelo, con cada cambio trazado");
  await page.waitForTimeout(4000);

  await grabadora.terminar();
});
