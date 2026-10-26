// Copia el worker de pdf.js a public/ para que el visor de planos lo cargue sin depender del bundler.
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const source = require.resolve("pdfjs-dist/build/pdf.worker.min.mjs");
const target = resolve(here, "../public/pdf.worker.min.mjs");

mkdirSync(dirname(target), { recursive: true });
copyFileSync(source, target);
