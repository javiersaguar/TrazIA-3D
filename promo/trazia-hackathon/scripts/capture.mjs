// Captura la UI real de TrazIA-3D (servidor local, datos de demostración sintéticos) a 1920×1080 @2x.
// Uso: node scripts/capture.mjs [base] [paso]
// Playwright se toma del proyecto web (no se instala aquí).
import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
const WEB = path.resolve(here, '../../../../TrazIA-3D-pulido/web/');
const require = createRequire(path.join(WEB, 'package.json'));
const { chromium } = require('@playwright/test');

const BASE = process.argv[2] ?? 'http://localhost:3350';
const ONLY = process.argv[3];
const OUT = path.resolve(here, '../public/captures');
fs.mkdirSync(OUT, { recursive: true });
const layout = fs.existsSync(path.join(OUT, 'layout.json')) ? JSON.parse(fs.readFileSync(path.join(OUT, 'layout.json'), 'utf8')) : {};

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: 'dark', reducedMotion: 'reduce' });
const page = await ctx.newPage();
const box = async (loc) => { const b = await loc.boundingBox(); return b && { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
const settle = async (ms = 1500) => { await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(ms); };

const steps = {
  async documentos() {
    await page.goto(`${BASE}/documentos`, { waitUntil: 'networkidle' });
    await settle(2500);
    await page.screenshot({ path: `${OUT}/documentos.png` });
    layout.documentos = {};
  },
  async revision() {
    await page.goto(`${BASE}/modelo?vista=revision`, { waitUntil: 'networkidle' });
    await settle(5000);
    await page.getByText('Diámetro de la virola').first().click();
    await settle(3000);
    await page.screenshot({ path: `${OUT}/revision.png` });
    const row0 = page.getByText('Diámetro de la virola').first();
    layout.revision_label = await box(row0);
    await page.getByRole('button', { name: /^Plano$/ }).first().click().catch(() => {});
    await settle(2500);
    await page.screenshot({ path: `${OUT}/revision-plano.png` });
    const row = page.getByText('Diámetro de la virola').first().locator('xpath=ancestor::*[self::button or self::li or @role="option" or @role="button"][1]');
    layout.revision = { row: await box(row).catch(() => null), pdf: await box(page.getByTestId('pdf-panel')).catch(() => null) };
  },
  async cambios() {
    await page.goto(`${BASE}/modelo?vista=cambios`, { waitUntil: 'networkidle' });
    await settle(8000);
    await page.screenshot({ path: `${OUT}/cambios.png` });
    layout.cambios = {};
  },
};

for (const [name, fn] of Object.entries(steps)) {
  if (ONLY && ONLY !== name) continue;
  try { await fn(); console.log('ok', name); } catch (e) { console.log('fallo', name, e.message); }
}
fs.writeFileSync(path.join(OUT, 'layout.json'), JSON.stringify(layout, null, 1));
await browser.close();
