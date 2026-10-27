import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

const report = JSON.parse(readFileSync(resolve(__dirname, "../../../docs/evidencias/fase1/estudio.json"), "utf8"));
const source = process.env.NEXT_PUBLIC_API_URL ? `${process.env.NEXT_PUBLIC_API_URL}/estudio` : "**/demo/json/estudio.json";

test("Bench y Estudio muestran el mismo informe y distinguen el bench v1", async ({ page }) => {
  await page.route(source, route => route.fulfill({ json: report }));
  await page.goto("/bench");
  const bench = page.getByTestId("study-bench");
  await expect(bench).toBeVisible();
  await expect(bench.getByText("0,389", { exact: true })).toBeVisible();
  await expect(bench).toContainText("24 equipos · 6 estilos medidos · 3 degradaciones");
  await page.getByLabel("Variante medida").selectOption("b_reglas-hdm");
  await expect(bench.getByText("0,280", { exact: true })).toBeVisible();
  await page.getByRole("radio", { name: "Bench de referencia v1", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Rúbrica del jurado", exact: true })).toBeVisible();
  await page.getByRole("radio", { name: "Estudio actual", exact: true }).click();
  await page.getByRole("link", { name: "Ver variantes, ablaciones y frontera de Pareto" }).click();
  await expect(page).toHaveURL(/\/estudio$/);
  await expect(page.getByRole("note")).toContainText("6 estilos medidos");
  await expect(page.getByRole("note")).not.toContainText("ocho proveedores");
});

test("Bench diferencia un error del estudio de la falta de resultados", async ({ page }) => {
  await page.route(source, route => route.fulfill({ status: 503, json: { detail: "Informe no disponible en la prueba" } }));
  await page.goto("/bench");
  await expect(page.getByRole("alert").filter({ hasText: "No se pudo cargar el estudio" })).toContainText("No se pudo cargar el estudio");
  await expect(page.getByRole("button", { name: "Reintentar", exact: true })).toBeVisible();
  await expect(page.getByText("Aún no hay resultados del estudio", { exact: true })).toHaveCount(0);
});

test("Bench muestra estado vacío sin cifras del estudio", async ({ page }) => {
  await page.route(source, route => route.fulfill({ json: { status: "empty", variants: [], detail: "Todavía sin medir" } }));
  await page.goto("/bench");
  await expect(page.getByText("Aún no hay resultados del estudio", { exact: true })).toBeVisible();
  await expect(page.getByTestId("study-bench")).toHaveCount(0);
});
