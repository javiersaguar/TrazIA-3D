// Genera src/lib/types/revision.ts a partir del esquema JSON del contrato.
// El esquema lo emite el núcleo Python: `uv run trazia schema -o generated/revision.schema.json`.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "json-schema-to-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const schemaPath = resolve(here, "../../generated/revision.schema.json");
const outPath = resolve(here, "../src/lib/types/revision.ts");

if (!existsSync(schemaPath)) {
  console.error(
    `No existe ${schemaPath}.\nGenéralo desde la raíz del repo con:\n  uv run trazia schema -o generated/revision.schema.json`,
  );
  process.exit(1);
}

const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const ts = await compile(schema, "Revision", {
  bannerComment:
    "/* Archivo generado por scripts/gen-types.mjs desde generated/revision.schema.json. No editar a mano. */",
  additionalProperties: false,
  strictIndexSignatures: true,
  style: { singleQuote: false, semi: true },
});

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, ts);
console.log(`Tipos generados en ${outPath}`);
