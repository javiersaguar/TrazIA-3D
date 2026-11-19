"""IFC4 de planta descompuesta: raíces por equipo, línea e infraestructura con subelementos.

Contrato C1 del plan de escenas 3D:

- Equipo raíz con su clase (IfcTank, IfcPump…), Name = Tag = TAG y sin representación propia.
  Sus puertos se anidan en él (IfcRelNests).
- Línea raíz: IfcElementAssembly (USERDEFINED, "Línea de proceso"). Sus puertos de entrada y
  salida se anidan en el subelemento de tramo.
- Infraestructura raíz: IfcElementAssembly ST-00.
- Subelementos agregados a su raíz (IfcRelAggregates) con Tag "TAG/clave", Name "TAG · Etiqueta",
  GlobalId estable y los psets TrazIA_Traceability y TrazIA_Dimensiones.

Todos los GlobalId salen de claves estables, así que el mismo subelemento conserva su GUID entre
revisiones y el fichero no cambia entre dos ejecuciones con la misma definición.
"""

import re
from functools import cache

import ifcopenshell
import ifcopenshell.api.context
import ifcopenshell.api.unit
from ifcopenshell import ifcopenshell_wrapper

from trazia.ifc import stable_guid, validate_ifc

from .process_geometry import PALETTE
from .process_mesh import TEMPLATES

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
ASSEMBLY = {"pipe": "Línea de proceso", "structure": "Infraestructura de planta"}
MAX_TRIANGLES = 95_000
MAX_IFC_BYTES = 3_500_000
SCHEMA = ifcopenshell_wrapper.schema_by_name("IFC4")


REAL = re.compile(r"-?\d+\.\d*(?:E[-+]?\d+)?")


def short_real(match) -> str:
    """Escribe un real STEP con la representación más corta que conserva su valor."""
    text = repr(float(match[0]))
    if "e" in text or "E" in text:
        text = f"{float(match[0]):.9f}".rstrip("0")
    return text if "." in text else text + "."


def compact(step: str) -> str:
    """ifcopenshell escribe los reales con 17 cifras; fuera de las cadenas se acortan."""
    pieces = step.split("'")
    for i in range(0, len(pieces), 2):
        pieces[i] = REAL.sub(short_real, pieces[i])
    return "'".join(pieces)


@cache
def predefined_values(ifc_class: str) -> set[str]:
    declaration = SCHEMA.declaration_by_name(ifc_class)
    for attribute in declaration.all_attributes():
        if attribute.name() == "PredefinedType":
            kind = attribute.type_of_attribute().declared_type()
            return set(kind.enumeration_items())
    return set()


def create_ifc(path, project, revision, equipment, lines, paths, parts):
    model = ifcopenshell.file(schema="IFC4")
    model.header.file_name.name = path.name
    model.header.file_name.time_stamp = "2026-01-01T00:00:00"
    model.header.file_name.author = ("TrazIA-3D",)
    model.header.file_name.authorization = "DRAFT"
    model.header.file_description.description = ("ViewDefinition [DesignTransferView]",)
    code = project.code

    def create(type_, **values):
        return model.create_entity(type_, **values)

    def root(ifc_class, key, name, **values):
        return create(ifc_class, GlobalId=stable_guid(f"{code}/{key}"), Name=name, **values)

    def placement(point, parent=None):
        location = create("IfcCartesianPoint", Coordinates=tuple(float(x) for x in point))
        axis = create("IfcAxis2Placement3D", Location=location)
        return create("IfcLocalPlacement", PlacementRelTo=parent, RelativePlacement=axis)

    def value(entry):
        if isinstance(entry, bool):
            return model.create_entity("IfcBoolean", entry)
        if isinstance(entry, int):
            return model.create_entity("IfcInteger", entry)
        if isinstance(entry, float):
            return model.create_entity("IfcReal", entry)
        return model.create_entity("IfcLabel", str(entry))

    def pset(key, name, properties, objects):
        values = [
            create("IfcPropertySingleValue", Name=prop, NominalValue=value(entry))
            for prop, entry in properties.items()
        ]
        definition = create(
            "IfcPropertySet",
            GlobalId=stable_guid(f"{code}/{key}/{name}"),
            Name=name,
            HasProperties=values,
        )
        create(
            "IfcRelDefinesByProperties",
            GlobalId=stable_guid(f"{code}/{key}/{name}/rel"),
            RelatedObjects=objects,
            RelatingPropertyDefinition=definition,
        )

    origin = placement((0.0, 0.0, 0.0))
    container = root("IfcProject", "project", code, LongName=project.name)
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
    site = root("IfcSite", "site", project.setting, ObjectPlacement=origin)
    building = root("IfcBuilding", "module", "Complejo de proceso", ObjectPlacement=origin)
    floor = root(
        "IfcBuildingStorey",
        "deck",
        "Nivel de proceso",
        ObjectPlacement=origin,
        Elevation=float(project.deck),
    )
    for parent, child in ((container, site), (site, building), (building, floor)):
        create(
            "IfcRelAggregates",
            GlobalId=stable_guid(f"{code}/{child.GlobalId}/spatial"),
            RelatingObject=parent,
            RelatedObjects=[child],
        )

    def finish(name, hexcolor):
        r, g, b = (int(hexcolor[i : i + 2], 16) / 255 for i in (1, 3, 5))
        color = create("IfcColourRgb", Name=name, Red=r, Green=g, Blue=b)
        shading = create("IfcSurfaceStyleShading", SurfaceColour=color, Transparency=0.0)
        return create("IfcSurfaceStyle", Name=name, Side="BOTH", Styles=[shading])

    materials = {}
    triangles = 0
    cache = {}

    def style(material):
        if material not in materials:
            materials[material] = finish(material, PALETTE[material])
        return materials[material]

    def faceset(mesh, material):
        coords = create("IfcCartesianPointList3D", CoordList=mesh.vertices)
        indices = [
            (face[0] + 1, face[n] + 1, face[n + 1] + 1)
            for face in mesh.faces
            for n in range(1, len(face) - 1)
        ]
        tessellation = create(
            "IfcTriangulatedFaceSet",
            Coordinates=coords,
            Closed=False,
            CoordIndex=indices,
        )
        create("IfcStyledItem", Item=tessellation, Styles=[style(material)], Name=material)
        return tessellation, len(indices)

    def representation(items, kind):
        return create(
            "IfcShapeRepresentation",
            ContextOfItems=body,
            RepresentationIdentifier="Body",
            RepresentationType=kind,
            Items=items,
        )

    def shared(kind, key, build):
        if (kind, key) not in cache:
            cache[kind, key] = build()
        return cache[kind, key]

    map_origin = create(
        "IfcAxis2Placement3D", Location=create("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    )

    def representation_map(items):
        return create(
            "IfcRepresentationMap",
            MappingOrigin=map_origin,
            MappedRepresentation=representation(items, "Tessellation"),
        )

    def template_map(key, material):
        def build():
            item, count = faceset(TEMPLATES[key], material)
            return representation_map([item]), count

        return shared("map", (key, material), build)

    def direction(ratios):
        return shared("dir", ratios, lambda: create("IfcDirection", DirectionRatios=ratios))

    def operator(origin, rotation):
        def build():
            x, y, z = (tuple(row[i] for row in rotation) for i in range(3))
            return create(
                "IfcCartesianTransformationOperator3D",
                Axis1=direction(x),
                Axis2=direction(y),
                LocalOrigin=create("IfcCartesianPoint", Coordinates=tuple(origin)),
                Scale=1.0,
                Axis3=direction(z),
            )

        return shared("op", (origin, rotation), build)

    identity = operator((0.0, 0.0, 0.0), ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))

    def shape(meshes):
        """Representación Body: caras propias (Tessellation) e instancias (IfcMappedItem).
        Si hay de las dos, las caras propias van en un mapa de un solo uso."""
        nonlocal triangles
        own, mapped = [], []
        for material, mesh in meshes.items():
            if mesh.faces:
                item, count = faceset(mesh, material)
                own.append(item)
                triangles += count
            for key, origin, rotation in mesh.instances:
                source, count = template_map(key, material)
                mapped.append(
                    create(
                        "IfcMappedItem",
                        MappingSource=source,
                        MappingTarget=operator(origin, rotation),
                    )
                )
                triangles += count
        if mapped and own:
            mapped.insert(
                0,
                create(
                    "IfcMappedItem",
                    MappingSource=representation_map(own),
                    MappingTarget=identity,
                ),
            )
        if mapped:
            shapes = [representation(mapped, "MappedRepresentation")]
        else:
            shapes = [representation(own, "Tessellation")]
        return create("IfcProductDefinitionShape", Representations=shapes)

    base = {
        "Dataset": "synthetic",
        "Draft": True,
        "ProcessProject": code,
        "Revision": revision,
    }
    roots = {}
    segments = {}
    for part in parts:
        if part.kind == "equipment":
            ifc_class = CLASSES[equipment[part.tag].family]
        else:
            ifc_class = "IfcElementAssembly"
        entity = root(ifc_class, part.tag, part.tag, Tag=part.tag, Description=part.name)
        entity.ObjectPlacement = origin
        if ifc_class == "IfcElementAssembly":
            entity.PredefinedType = "USERDEFINED"
            entity.ObjectType = ASSEMBLY[part.kind]
        properties = {**base, "Component": part.tag, "Role": part.kind, "Description": part.name}
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
                RackHeightM=line.rack_z,
            )
            if revision in ("A", "B"):
                properties["SourceWorkbook"] = f"Lista_{code}_rev{revision}.xlsx"
        pset(part.tag, "TrazIA_Traceability", properties, [entity])

        children = []
        for comp in part.components:
            tag = f"{part.tag}/{comp.key}"
            child = root(
                comp.ifc_class,
                tag,
                f"{part.tag} · {comp.label}",
                Tag=tag,
                Description=comp.role or comp.label,
                ObjectPlacement=origin,
                Representation=shape(comp.meshes),
            )
            allowed = predefined_values(comp.ifc_class)
            kind = comp.predefined if comp.predefined in allowed else None
            if kind is None and "USERDEFINED" in allowed:
                kind = "USERDEFINED"
            if kind:
                child.PredefinedType = kind
            if kind == "USERDEFINED":
                child.ObjectType = comp.object_type or comp.label
            pset(
                tag,
                "TrazIA_Traceability",
                {
                    **base,
                    "Component": tag,
                    "ParentComponent": part.tag,
                    "Role": "component",
                    "Description": comp.label,
                },
                [child],
            )
            if comp.dims:
                pset(tag, "TrazIA_Dimensiones", dict(comp.dims), [child])
            children.append(child)
            if part.kind == "pipe" and comp.key == "tramo":
                segments[part.tag] = child
        create(
            "IfcRelAggregates",
            GlobalId=stable_guid(f"{code}/{part.tag}/aggregates"),
            RelatingObject=entity,
            RelatedObjects=children,
        )
        roots[part.tag] = entity
    create(
        "IfcRelContainedInSpatialStructure",
        GlobalId=stable_guid(f"{code}/containment"),
        RelatedElements=list(roots.values()),
        RelatingStructure=floor,
    )

    nests = {}

    def port(owner, host, name, source, point):
        result = root(
            "IfcDistributionPort",
            f"{owner}/{name}",
            name,
            FlowDirection="SOURCE" if source else "SINK",
            ObjectPlacement=placement(point, origin),
        )
        nests.setdefault(owner, (host, []))[1].append(result)
        return result

    for tag, line in lines.items():
        start, end = paths[tag][0], paths[tag][-1]
        a = port(line.start, roots[line.start], tag + "/salida", True, start)
        b = port(line.end, roots[line.end], tag + "/entrada", False, end)
        pipe_start = port(tag, segments[tag], "entrada", False, start)
        pipe_end = port(tag, segments[tag], "salida", True, end)
        for i, (from_, to) in enumerate(((a, pipe_start), (pipe_end, b))):
            create(
                "IfcRelConnectsPorts",
                GlobalId=stable_guid(f"{code}/{tag}/link{i}"),
                RelatingPort=from_,
                RelatedPort=to,
            )
    for owner, (host, ports) in nests.items():
        create(
            "IfcRelNests",
            GlobalId=stable_guid(f"{code}/{owner}/ports"),
            RelatingObject=host,
            RelatedObjects=ports,
        )

    problems = validate_ifc(model)
    if problems:
        raise ValueError(f"{path.name}: {problems[0]['message']}")
    if triangles > MAX_TRIANGLES:
        raise ValueError(
            f"{path.name}: supera el presupuesto de {MAX_TRIANGLES:,} triángulos ({triangles:,})"
        )
    # La huella y el tamaño del catálogo se mantienen entre Windows y Linux.
    content = compact(model.to_string().replace("\r\n", "\n"))
    path.write_bytes(content.encode("utf-8"))
    return triangles
