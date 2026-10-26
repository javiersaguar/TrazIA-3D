import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const root = fileURLToPath(new URL("../../../../", import.meta.url));
const source = ["import json", "from trazia.api.app import create_app",
  "print(json.dumps(create_app().openapi(), ensure_ascii=False))"].join("\n");
const schema = JSON.parse(execFileSync("uv", ["run", "--extra", "api", "python", "-c", source], {
  cwd: root, encoding: "utf8", maxBuffer: 10 * 1024 * 1024,
  env: { ...process.env, PYTHONIOENCODING: "utf-8" },
}));
writeFileSync(fileURLToPath(new URL("./openapi.json", import.meta.url)), JSON.stringify(schema, null, 2) + "\n");
const ast = await openapiTS(schema, { defaultNonNullable: false });
writeFileSync(fileURLToPath(new URL("./schema.ts", import.meta.url)),
  "/* Tipos del contrato HTTP. Actualizar con pnpm gen:api. */\n" + astToString(ast));
