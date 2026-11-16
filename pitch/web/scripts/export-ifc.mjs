import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import webIfc from "web-ifc";

const api = new webIfc.IfcAPI();
await api.Init();
const output = new URL("../generated/", import.meta.url);
mkdirSync(output, { recursive: true });
try {
  for (const revision of ["a", "b"]) {
    const file = new URL(`../../../web/public/demo/ifc/rev_${revision}.ifc`, import.meta.url);
    const model = api.OpenModel(readFileSync(file), { COORDINATE_TO_ORIGIN: true });
    if (api.GetModelSchema(model) !== "IFC4") throw new Error("Se esperaba IFC4");
    const parts = [];
    try {
      api.StreamAllMeshes(model, ({ geometries }) => {
        for (let i = 0; i < geometries.size(); i++) {
          const placed = geometries.get(i);
          const geometry = api.GetGeometry(model, placed.geometryExpressID);
          try {
            const vertices = api.GetVertexArray(geometry.GetVertexData(), geometry.GetVertexDataSize());
            const faces = api.GetIndexArray(geometry.GetIndexData(), geometry.GetIndexDataSize());
            const m = placed.flatTransformation;
            const positions = [];
            for (let j = 0; j < vertices.length; j += 6) {
              const [x, y, z] = vertices.subarray(j, j + 3);
              positions.push([
                m[0] * x + m[4] * y + m[8] * z + m[12],
                -(m[2] * x + m[6] * y + m[10] * z + m[14]),
                m[1] * x + m[5] * y + m[9] * z + m[13],
              ]);
            }
            parts.push({ positions, indices: Array.from(faces) });
          } finally {
            geometry.delete();
          }
        }
      }, true);
    } finally {
      api.CloseModel(model);
    }
    if (!parts.length) throw new Error(`IFC ${revision}: sin geometría`);
    writeFileSync(new URL(`rev-${revision}.json`, output), JSON.stringify(parts));
    console.log(`Rev. ${revision.toUpperCase()}: ${parts.reduce((n, p) => n + p.indices.length / 3, 0)} triángulos del IFC`);
  }
} finally {
  api.Dispose();
}
