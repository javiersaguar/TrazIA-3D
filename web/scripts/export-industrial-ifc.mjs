// Envuelve las mallas del catálogo en IFC4 usando el mismo lector que utiliza el visor.
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import webIfc from "web-ifc";

const { IFC4, IFCBUILDINGELEMENTPROXY, IfcAPI } = webIfc;
const directory = new URL("../public/demo/industriales/", import.meta.url);
const work = new URL("../../generated/", import.meta.url);
const index = readFileSync(new URL("industrial-designs.json", work), "utf8");
const { designs } = JSON.parse(index);
const meshes = JSON.parse(readFileSync(new URL("industrial-meshes.json", work), "utf8"));
const api = new IfcAPI();
await api.Init();

const alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$";
function guid(id) {
  const hash = createHash("sha256").update(id).digest("hex").slice(0, 32);
  let value = BigInt("0x" + hash);
  let encoded = "";
  for (let i = 0; i < 22; i++) {
    encoded = alphabet[Number(value & 63n)] + encoded;
    value >>= 6n;
  }
  return new IFC4.IfcGloballyUniqueId(encoded);
}

function exportDesign(design, parts) {
  const model = api.CreateModel({
    schema: "IFC4",
    name: design.ifc,
    description: ["Diseno conceptual sintetico DRAFT"],
    authors: ["TrazIA-3D"],
    organizations: ["TrazIA-3D"],
    authorization: "DRAFT",
  });
  const label = (text) => new IFC4.IfcLabel(text);
  const text = (value) => new IFC4.IfcText(value);
  const length = (value) => new IFC4.IfcLengthMeasure(value);
  const id = (key) => guid("trazia-industrial/" + design.tag + "/" + key);
  const write = (entity) => {
    api.WriteLine(model, entity);
    return entity;
  };
  try {
    const point = write(new IFC4.IfcCartesianPoint([0, 0, 0].map(length)));
    const axis = write(new IFC4.IfcAxis2Placement3D(point, null, null));
    const placement = write(new IFC4.IfcLocalPlacement(null, axis));
    const unit = write(new IFC4.IfcSIUnit(IFC4.IfcUnitEnum.LENGTHUNIT, IFC4.IfcSIPrefix.MILLI, IFC4.IfcSIUnitName.METRE));
    const units = write(new IFC4.IfcUnitAssignment([unit]));
    const context = write(new IFC4.IfcGeometricRepresentationContext(
      null, label("Model"), new IFC4.IfcDimensionCount(3), new IFC4.IfcReal(0.0001), axis, null,
    ));
    const project = write(new IFC4.IfcProject(
      id("project"), null, label(design.tag), text("Diseno conceptual sintetico"),
      null, label(design.name), label("DRAFT"), [context], units,
    ));
    const composition = IFC4.IfcElementCompositionEnum.ELEMENT;
    const site = write(new IFC4.IfcSite(
      id("site"), null, label("Catalogo sintetico"), null, null, placement,
      null, null, composition, null, null, null, null, null,
    ));
    const building = write(new IFC4.IfcBuilding(
      id("building"), null, label("Equipos de proceso"), null, null, placement,
      null, null, composition, null, null, null,
    ));
    const storey = write(new IFC4.IfcBuildingStorey(
      id("storey"), null, label("Implantacion conceptual"), null, null, placement,
      null, null, composition, length(0),
    ));
    const hierarchy = [[project, site], [site, building], [building, storey]];
    for (const [index, [parent, child]] of hierarchy.entries()) {
      write(new IFC4.IfcRelAggregates(id("aggregate/" + index), null, null, null, parent, [child]));
    }
    const products = parts.map(({ name, vertices, triangles }) => {
      const coords = write(new IFC4.IfcCartesianPointList3D(vertices.map((v) => v.map(length))));
      const indices = triangles.map((face) => face.map((i) => new IFC4.IfcPositiveInteger(i + 1)));
      const mesh = write(new IFC4.IfcTriangulatedFaceSet(coords, null, new IFC4.IfcBoolean(true), indices, null));
      const rep = write(new IFC4.IfcShapeRepresentation(context, label("Body"), label("Tessellation"), [mesh]));
      const shape = write(new IFC4.IfcProductDefinitionShape(null, null, [rep]));
      return write(new IFC4.IfcBuildingElementProxy(
        id("part/" + name), null, label(name), text("Componente exterior conceptual DRAFT"),
        label(design.family), placement, shape, new IFC4.IfcIdentifier(design.tag), null,
      ));
    });
    write(new IFC4.IfcRelContainedInSpatialStructure(id("containment"), null, null, null, products, storey));
    const property = (key, value) => write(new IFC4.IfcPropertySingleValue(new IFC4.IfcIdentifier(key), null, value, null));
    const trace = write(new IFC4.IfcPropertySet(id("trace"), null, label("TrazIA_Traceability"), null, [
      property("Dataset", label("synthetic")),
      property("Draft", new IFC4.IfcBoolean(true)),
      property("Family", label(design.family)),
      property("Origin", label("Parametric conceptual model")),
    ]));
    write(new IFC4.IfcRelDefinesByProperties(id("trace/association"), null, null, null, products, trace));
    // Cabecera estable de la colección, independiente de cuándo se regenere.
    const step = Buffer.from(api.SaveModel(model)).toString("utf8")
      .replace(/\/\*[\s\S]*?\*\/\r?\n/, "")
      .replace(/^FILE_NAME\([^\r\n]*\);/m,
        `FILE_NAME('${design.ifc}','2026-11-16T00:00:00',('TrazIA-3D'),('TrazIA-3D'),'TrazIA-3D','TrazIA-3D','DRAFT');`);
    return Buffer.from(step, "utf8");
  } finally {
    api.CloseModel(model);
  }
}

function verify(bytes, design, parts) {
  const model = api.OpenModel(bytes);
  try {
    const products = api.GetLineIDsWithType(model, IFCBUILDINGELEMENTPROXY);
    let rendered = 0;
    api.StreamAllMeshes(model, (mesh) => {
      if (mesh.geometries.size() > 0) rendered++;
    });
    if (products.size() !== parts.length || rendered !== parts.length) {
      throw new Error(`${design.tag}: ${products.size()} componentes, ${rendered} renderizables, ${parts.length} esperados`);
    }
  } finally {
    api.CloseModel(model);
  }
}

for (const design of designs) {
  const parts = meshes[design.tag];
  const bytes = exportDesign(design, parts);
  verify(bytes, design, parts);
  writeFileSync(new URL(design.ifc, directory), bytes);
}
writeFileSync(new URL("../src/features/documents/industrial-designs.json", import.meta.url), index);
console.log(`${designs.length} IFC4 conceptuales reabiertos y verificados con WebIFC.`);
