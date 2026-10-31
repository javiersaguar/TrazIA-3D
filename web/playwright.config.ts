import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
const connected = Boolean(process.env.NEXT_PUBLIC_API_URL);
const cpuOnly = process.env.PW_CPU_ONLY === "1";
const port = Number(process.env.PW_PORT ?? (connected ? 3100 : 3200));
const apiURL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const root = resolve(__dirname, "..");

/*
  Usa el Google Chrome instalado en el sistema (channel "chrome") para no descargar navegadores.
  Si no tienes Chrome: PW_CHANNEL=msedge pnpm test:e2e
  - humo: recorre las pantallas y las interacciones clave.
  - capturas: guarda capturas de cada pantalla en oscuro y claro en docs/capturas/.
*/
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45_000,
  expect: { timeout: cpuOnly ? 15_000 : 5_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${port}`,
    channel: process.env.PW_CHANNEL ?? "chrome",
    viewport: { width: 1600, height: 940 },
    locale: "es-ES",
    trace: "retain-on-failure",
    launchOptions: cpuOnly ? { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] } : undefined,
  },
  projects: [
    { name: "humo", testMatch: /(?:humo|api|study|3d)\.spec\.ts/ },
    { name: "capturas", testMatch: /capturas\.spec\.ts/ },
  ],
  webServer: [
    ...(connected && !process.env.PW_EXTERNAL_API ? [{
      command: "uv run --extra api python -m trazia.api", cwd: root,
      url: `${apiURL}/health`, reuseExistingServer: false, timeout: 120_000,
      env: { TRAZIA_DATA: `${root}/generated/e2e-api-${process.pid}`,
        TRAZIA_ROOT: root, TRAZIA_PORT: new URL(apiURL).port || "8000", TRAZIA_QUEUE: "process",
        TRAZIA_CORRECTIONS_FILE: `${root}/generated/e2e-api-${process.pid}/correcciones.jsonl` },
    }] : []),
    { command: process.env.PW_USE_BUILD ? `corepack pnpm exec next start --port ${port}` : `corepack pnpm@10.18.0 dev --port ${port}`,
      url: `http://localhost:${port}/proyecto`, reuseExistingServer: false, timeout: 120_000 },
  ],
});
