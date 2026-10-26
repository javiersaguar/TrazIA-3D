import { defineConfig } from "@playwright/test";

/*
  Usa el Google Chrome instalado en el sistema (channel "chrome") para no descargar navegadores.
  Si no tienes Chrome: PW_CHANNEL=msedge pnpm test:e2e
  - humo: recorre las pantallas y las interacciones clave.
  - capturas: guarda capturas de cada pantalla en oscuro y claro en docs/capturas/.
*/
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45_000,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    channel: process.env.PW_CHANNEL ?? "chrome",
    viewport: { width: 1600, height: 940 },
    locale: "es-ES",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "humo", testMatch: /humo\.spec\.ts/ },
    { name: "capturas", testMatch: /capturas\.spec\.ts/ },
  ],
  webServer: {
    command: "corepack pnpm@10.18.0 dev",
    url: "http://localhost:3000/proyecto",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
