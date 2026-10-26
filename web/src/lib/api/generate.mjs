import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const schema = JSON.parse(readFileSync(new URL("./openapi.json", import.meta.url), "utf8"));
const ast = await openapiTS(schema, { defaultNonNullable: false });
writeFileSync(fileURLToPath(new URL("./schema.ts", import.meta.url)),
  "/* Tipos del contrato HTTP. Actualizar con pnpm gen:api. */\n" + astToString(ast));
