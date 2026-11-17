import { IFC4, IFCBUILDINGELEMENTPROXY, type IfcAPI } from "web-ifc";

import type { DesignSpec, PartMesh } from "./parametric";

/*
  Mismo IFC4 que web/scripts/export-industrial-ifc.mjs, escrito en el navegador: proyecto, sitio,
  edificio y planta, una IfcBuildingElementProxy con IfcTriangulatedFaceSet por pieza y el pset
  TrazIA_Traceability. Los GUID salen del tag y del nombre de la pieza, como en el exportador, así
  que una pieza conserva su GUID aunque cambien sus medidas.
*/

const ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$";

export async function ifcGuid(id: string): Promise<string> {
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(id)));
  const hex = Array.from(digest.slice(0, 16), (byte) => byte.toString(16).padStart(2, "0")).join("");
  let value = BigInt("0x" + hex);
  let encoded = "";
  for (let i = 0; i < 22; i++) {
    encoded = ALPHABET[Number(value & 63n)] + encoded;
    value >>= 6n;
  }
  return encoded;
}

export async function writeDesignIfc(api: IfcAPI, design: DesignSpec, parts: PartMesh[], edited: boolean) {
  const filename = `${design.tag}-A${edited ? "-editado" : ""}.ifc`;
  const model = api.CreateModel({
    schema: "IFC4",
    name: filename,
    description: [edited ? "Diseno conceptual sintetico DRAFT editado en TrazIA-3D" : "Diseno conceptual sintetico DRAFT"],
    authors: ["TrazIA-3D"],
    organizations: ["TrazIA-3D"],
    authorization: "DRAFT",
  });
  const label = (text: string) => new IFC4.IfcLabel(text);
  const text = (value: string) => new IFC4.IfcText(value);
  const length = (value: number) => new IFC4.IfcLengthMeasure(value);
  const id = async (key: string) => new IFC4.IfcGloballyUniqueId(await ifcGuid(`trazia-industrial/${design.tag}/${key}`));
  const write = <T extends object>(entity: T): T => {
    api.WriteLine(model, entity as never);
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
      await id("project"), null, label(design.tag), text("Diseno conceptual sintetico"),
      null, label(design.name), label("DRAFT"), [context], units,
    ));
    const composition = IFC4.IfcElementCompositionEnum.ELEMENT;
    const site = write(new IFC4.IfcSite(
      await id("site"), null, label("Catalogo sintetico"), null, null, placement,
      null, null, composition, null, null, null, null, null,
    ));
    const building = write(new IFC4.IfcBuilding(
      await id("building"), null, label("Equipos de proceso"), null, null, placement,
      null, null, composition, null, null, null,
    ));
    const storey = write(new IFC4.IfcBuildingStorey(
      await id("storey"), null, label("Implantacion conceptual"), null, null, placement,
      null, null, composition, length(0),
    ));
    const hierarchy = [[project, site], [site, building], [building, storey]] as const;
    for (const [index, [parent, child]] of hierarchy.entries()) {
      write(new IFC4.IfcRelAggregates(await id(`aggregate/${index}`), null, null, null, parent, [child]));
    }
    const products = [];
    for (const { name, vertices, triangles } of parts) {
      const coords = write(new IFC4.IfcCartesianPointList3D(vertices.map((v) => v.map(length))));
      const indices = triangles.map((face) => face.map((i) => new IFC4.IfcPositiveInteger(i + 1)));
      const mesh = write(new IFC4.IfcTriangulatedFaceSet(coords, null, new IFC4.IfcBoolean(true), indices, null));
      const rep = write(new IFC4.IfcShapeRepresentation(context, label("Body"), label("Tessellation"), [mesh]));
      const shape = write(new IFC4.IfcProductDefinitionShape(null, null, [rep]));
      products.push(write(new IFC4.IfcBuildingElementProxy(
        await id(`part/${name}`), null, label(name), text("Componente exterior conceptual DRAFT"),
        label(design.family), placement, shape, new IFC4.IfcIdentifier(design.tag), null,
      )));
    }
    write(new IFC4.IfcRelContainedInSpatialStructure(await id("containment"), null, null, null, products, storey));
    const property = (key: string, value: IFC4.IfcLabel | IFC4.IfcBoolean) =>
      write(new IFC4.IfcPropertySingleValue(new IFC4.IfcIdentifier(key), null, value, null));
    const trace = write(new IFC4.IfcPropertySet(await id("trace"), null, label("TrazIA_Traceability"), null, [
      property("Dataset", label("synthetic")),
      property("Draft", new IFC4.IfcBoolean(true)),
      property("Family", label(design.family)),
      property("Origin", label(edited ? "Parametric conceptual model edited in Modelo" : "Parametric conceptual model")),
    ]));
    write(new IFC4.IfcRelDefinesByProperties(await id("trace/association"), null, null, null, products, trace));
    return { bytes: api.SaveModel(model), filename };
  } finally {
    api.CloseModel(model);
  }
}

/** Reabre el IFC y cuenta las piezas con geometría: lo que el visor podrá dibujar. */
export function renderableParts(api: IfcAPI, bytes: Uint8Array) {
  const model = api.OpenModel(bytes);
  try {
    const products = api.GetLineIDsWithType(model, IFCBUILDINGELEMENTPROXY).size();
    let rendered = 0;
    api.StreamAllMeshes(model, (mesh) => {
      if (mesh.geometries.size() > 0) rendered++;
    });
    return { products, rendered };
  } finally {
    api.CloseModel(model);
  }
}
