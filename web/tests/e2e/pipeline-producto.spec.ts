import { expect, test } from "@playwright/test";

test("estrategias sin conexiones atravesando tarjetas ajenas", async ({ page }) => {
  await page.goto("/pipeline");
  const selector = page.getByLabel("Estrategia del grafo");
  await expect(selector).toBeVisible();
  for (const strategy of ["a_vision", "b_reglas", "c_rag", "d_hibrido"]) {
    await selector.selectOption(strategy);
    await expect(page.locator('[data-stage="rag"]')).toHaveCount(["c_rag", "d_hibrido"].includes(strategy) ? 1 : 0);
    await expect(page.locator('[data-stage="extract_tables"]')).toHaveCount(["b_reglas", "d_hibrido"].includes(strategy) ? 1 : 0);
    await expect(page.locator(".react-flow__edge")).toHaveCount(strategy === "d_hibrido" ? 23 : strategy === "c_rag" ? 11 : 13);
    await page.waitForTimeout(400); // Termina el encuadre antes del contraste geométrico.
    const crossings = await page.evaluate(() => {
      const nodes = [...document.querySelectorAll<HTMLElement>("[data-stage]")].map(el => ({ id: el.dataset.stage, rect: el.getBoundingClientRect() }));
      const collisions: string[] = [];
      for (const edge of document.querySelectorAll(".react-flow__edge")) {
        const [source, target] = edge.getAttribute("data-id")!.split("-");
        const path = edge.querySelector<SVGPathElement>(".react-flow__edge-path")!;
        const matrix = path.getScreenCTM()!;
        for (let d = 0; d < path.getTotalLength(); d += 4) {
          const p = path.getPointAtLength(d).matrixTransform(matrix);
          for (const {id, rect:r} of nodes) {
            if (id !== source && id !== target && p.x > r.left + 2 && p.x < r.right - 2 && p.y > r.top + 2 && p.y < r.bottom - 2) collisions.push(`${source}->${target} cruza ${id}`);
          }
        }
      }
      return [...new Set(collisions)];
    });
    expect(crossings, strategy).toEqual([]);
  }
  await page.evaluate(() => { document.documentElement.dataset.theme = "dark"; document.documentElement.classList.remove("light"); document.documentElement.classList.add("dark"); });
  await page.screenshot({ path: "../docs/capturas/pipeline-d-oscuro.png", fullPage: true });
  await page.evaluate(() => { document.documentElement.dataset.theme = "light"; document.documentElement.classList.remove("dark"); document.documentElement.classList.add("light"); });
  await page.screenshot({ path: "../docs/capturas/pipeline-d-claro.png", fullPage: true });
});

test("reproducción, pausa, seguimiento, búsqueda de etapa y movimiento reducido", async ({ page }) => {
  await page.goto("/pipeline");
  await page.getByLabel("Estrategia del grafo").selectOption("d_hibrido");
  await page.getByRole("button", { name: "Seguir etapa", exact:true }).click();
  await expect(page.getByRole("button", { name: "Seguir etapa", exact:true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Reproducir explicación", exact:true }).click();
  await expect(page.getByLabel("Posición en el recorrido")).not.toHaveValue("0", { timeout: 7000 });
  await page.getByRole("button", { name: "Pausar", exact:true }).click();
  const position = await page.getByLabel("Posición en el recorrido").inputValue();
  await page.waitForTimeout(2800);
  await expect(page.getByLabel("Posición en el recorrido")).toHaveValue(position);
  await page.getByLabel("Posición en el recorrido").fill("8");
  await expect(page.locator('[data-stage="geometry2d"]')).toHaveAttribute("data-active", "true");
  await page.getByRole("button", { name: "Ampliar grafo",exact:true }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", {name:"Ampliar grafo",exact:true})).toBeVisible();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.getByRole("button", {name:"Reproducir explicación",exact:true})).toBeDisabled();
  await page.getByRole("button", {name:"Etapa siguiente",exact:true}).click();
  await expect(page.getByLabel("Posición en el recorrido")).toHaveValue("9");
});


test("eventos sin API, teclado y ancho móvil", async ({ page }) => {
  test.skip(Boolean(process.env.NEXT_PUBLIC_API_URL), "Comprueba específicamente la ausencia de API");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/pipeline");
  await page.getByRole("button", { name: "Explorar Ingesta", exact: true }).press("Enter");
  await expect(page.getByLabel("Posición en el recorrido")).toHaveValue("0");
  await page.getByRole("button", { name: "Eventos reales", exact:true }).click();
  await expect(page.getByText("Sin API conectada. La simulación de demo no acredita ejecución real.", {exact:true})).toBeVisible();
  await expect(page.locator('[data-stage][data-active="true"]')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
});


test("el grafo observa un trabajo real por SSE", async ({ page }) => {
  test.skip(!process.env.NEXT_PUBLIC_API_URL, "Requiere API aislada");
  await page.goto("/pipeline");
  await page.getByRole("button", {name: "Eventos reales", exact: true}).click();
  await page.getByRole("button", {name: "Procesar demo", exact: true}).click();
  await expect(page.getByText(/Pipeline: último trabajo/)).toBeVisible({timeout: 30000});
  await page.getByRole("button", {name: "Explorar IFC", exact: true}).press("Enter");
  await expect(page.locator('[data-stage="ifc"]')).toHaveAttribute("data-active", "true");
  await expect(page.locator('[data-stage="ifc"]')).toContainText("eventos OK");
  await expect(page.getByRole("cell", {name: /IFC4 DRAFT almacenado/})).toBeVisible();
});
