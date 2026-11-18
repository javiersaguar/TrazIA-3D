"""IFC4 de planta con conexiones de puertos y GUID estables por pieza."""

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.nest
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.unit
from process_geometry import PALETTE

from trazia.ifc import stable_guid, validate_ifc

CLASSES = {
    "horizontal": "IfcTank",
    "vertical": "IfcTank",
    "column": "IfcTank",
    "tank": "IfcTank",
    "pump": "IfcPump",
    "compressor": "IfcCompressor",
    "air-cooler": "IfcHeatExchanger",
    "vaporizer": "IfcHeatExchanger",
    "cyclone": "IfcFilter",
    "arm": "IfcUnitaryEquipment",
    "manifold": "IfcPipeFitting",
}


def create_ifc(path, project, revision, equipment, lines, paths, parts):
    model = ifcopenshell.file(schema="IFC4")
    model.header.file_name.name = path.name
    model.header.file_name.time_stamp = "2026-01-01T00:00:00"
    model.header.file_name.author = ("TrazIA-3D",)
    model.header.file_name.authorization = "DRAFT"
    model.header.file_description.description = ("ViewDefinition [DesignTransferView]",)

    def root(ifc_class, key, name):
        entity = ifcopenshell.api.root.create_entity(model, ifc_class=ifc_class, name=name)
        entity.GlobalId = stable_guid(f"{project.code}/{key}")
        return entity

    def create(type_, **values):
        return model.create_entity(type_, **values)

    def placement(point, parent=None):
        location = create("IfcCartesianPoint", Coordinates=tuple(float(x) for x in point))
        axis = create("IfcAxis2Placement3D", Location=location)
        return create("IfcLocalPlacement", PlacementRelTo=parent, RelativePlacement=axis)

    origin = placement((0.0, 0.0, 0.0))
    container = root("IfcProject", "project", project.code)
    container.LongName = project.name
    units = [
        ifcopenshell.api.unit.add_si_unit(model, unit_type=kind)
        for kind in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT", "PLANEANGLEUNIT")
    ]
    ifcopenshell.api.unit.assign_unit(model, units=units)
    context = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context,
    )
    site = root("IfcSite", "site", project.setting)
    building = root("IfcBuilding", "module", "Complejo de proceso")
    floor = root("IfcBuildingStorey", "deck", "Nivel de proceso")
    for parent, child in ((container, site), (site, building), (building, floor)):
        ifcopenshell.api.aggregate.assign_object(model, products=[child], relating_object=parent)

    def finish(name, hexcolor):
        r, g, b = (int(hexcolor[i : i + 2], 16) / 255 for i in (1, 3, 5))
        color = create("IfcColourRgb", Name=name, Red=r, Green=g, Blue=b)
        shading = create("IfcSurfaceStyleShading", SurfaceColour=color, Transparency=0.0)
        return create("IfcSurfaceStyle", Name=name, Side="BOTH", Styles=[shading])

    materials = {name: finish(name, color) for name, color in PALETTE.items()}
    products = {}
    triangles = 0
    for part in parts:
        if part.kind == "equipment":
            ifc_class = CLASSES[equipment[part.tag].family]
        elif part.kind == "pipe":
            ifc_class = "IfcPipeSegment"
        else:
            ifc_class = "IfcBuildingElementProxy"
        entity = root(ifc_class, part.tag, part.tag)
        entity.Description = part.name
        entity.ObjectPlacement = origin
        entity.Tag = part.tag
        items = []
        for material, mesh in part.meshes.items():
            if not mesh.faces:
                continue
            coords = create("IfcCartesianPointList3D", CoordList=mesh.vertices)
            indices = [
                (face[0] + 1, face[n] + 1, face[n + 1] + 1)
                for face in mesh.faces
                for n in range(1, len(face) - 1)
            ]
            triangles += len(indices)
            tessellation = create(
                "IfcTriangulatedFaceSet",
                Coordinates=coords,
                Closed=True,
                CoordIndex=indices,
            )
            create("IfcStyledItem", Item=tessellation, Styles=[materials[material]], Name=material)
            items.append(tessellation)
        representation = create(
            "IfcShapeRepresentation",
            ContextOfItems=body,
            RepresentationIdentifier="Body",
            RepresentationType="Tessellation",
            Items=items,
        )
        entity.Representation = create(
            "IfcProductDefinitionShape", Representations=[representation]
        )
        trace = ifcopenshell.api.pset.add_pset(model, product=entity, name="TrazIA_Traceability")
        trace.GlobalId = stable_guid(f"{project.code}/{part.tag}/trace")
        properties = {
            "Dataset": "synthetic",
            "Draft": True,
            "ProcessProject": project.code,
            "Revision": revision,
            "Component": part.tag,
            "Role": part.kind,
            "Description": part.name,
        }
        if part.tag in equipment:
            item = equipment[part.tag]
            length, width, height = item.size
            properties.update(
                Service=item.service,
                NominalLengthM=float(length),
                NominalWidthM=float(width),
                NominalHeightM=float(height),
            )
            if revision in ("A", "B"):
                properties.update(
                    SourceGA=f"GAD_{item.tag}_rev{revision}.pdf",
                    SourceWorkbook=f"HDM_{item.tag}_rev{revision}.xlsx",
                )
        if part.tag in lines:
            line = lines[part.tag]
            properties.update(
                Fluid=line.fluid,
                NominalDiameterMM=line.dn,
                FromTag=line.start,
                ToTag=line.end,
                RackElevationM=float(project.deck + line.rack_z),
            )
            if revision in ("A", "B"):
                properties["SourceWorkbook"] = f"Lista_{project.code}_rev{revision}.xlsx"
        ifcopenshell.api.pset.edit_pset(
            model,
            pset=trace,
            properties=properties,
        )
        products[part.tag] = entity
    create(
        "IfcRelContainedInSpatialStructure",
        GlobalId=stable_guid(f"{project.code}/containment"),
        RelatedElements=list(products.values()),
        RelatingStructure=floor,
    )

    def port(owner, name, source, point):
        result = root("IfcDistributionPort", f"{owner}/{name}", name)
        result.FlowDirection = "SOURCE" if source else "SINK"
        result.ObjectPlacement = placement(point, origin)
        ifcopenshell.api.nest.assign_object(
            model,
            related_objects=[result],
            relating_object=products[owner],
        )
        return result

    for tag, line in lines.items():
        start, end = paths[tag][0], paths[tag][-1]
        a = port(line.start, tag + "/salida", True, start)
        b = port(line.end, tag + "/entrada", False, end)
        pipe_start = port(tag, "entrada", False, start)
        pipe_end = port(tag, "salida", True, end)
        for i, (from_, to) in enumerate(((a, pipe_start), (pipe_end, b))):
            create(
                "IfcRelConnectsPorts",
                GlobalId=stable_guid(f"{project.code}/{tag}/link{i}"),
                RelatingPort=from_,
                RelatedPort=to,
            )

    problems = validate_ifc(model)
    if problems:
        raise ValueError(f"{path.name}: {problems[0]['message']}")
    if triangles > 45_000:
        raise ValueError(f"{path.name}: supera el presupuesto de 45.000 triángulos ({triangles})")
    # La huella y el tamaño del catálogo se mantienen entre Windows y Linux.
    content = model.to_string().replace("\r\n", "\n")
    path.write_bytes(content.encode("utf-8"))
    return triangles
