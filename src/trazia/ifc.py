import json
import math
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import ifcopenshell.guid

from .model import Revision, fields


def stable_guid(key: str) -> str:
    return ifcopenshell.guid.compress(uuid5(NAMESPACE_URL, f"trazia:{key}").hex)


def build_ifc(revision: Revision, *, draft: bool = True) -> ifcopenshell.file:
    revision = Revision.model_validate_json(revision.model_dump_json())
    pending = revision.pending_review()
    if pending and not draft:
        raise ValueError(
            "Hay campos sin revisar: " + ", ".join(pending) + ". Use --draft para borrador."
        )
    if not draft and revision.approval is None:
        raise ValueError("Falta aprobación humana de esta revisión. Use --draft para borrador.")
    model = ifcopenshell.file(schema="IFC4")
    base = revision.project_id

    def root(ifc_class, name, key, **kwargs):
        entity = ifcopenshell.api.root.create_entity(
            model, ifc_class=ifc_class, name=name, **kwargs
        )
        entity.GlobalId = stable_guid(f"{base}/{key}")
        return entity

    project = root("IfcProject", revision.project_id, "project")
    units = [
        ifcopenshell.api.unit.add_si_unit(model, unit_type=t)
        for t in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT")
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
    site = root("IfcSite", revision.project_id, "site")
    building = root("IfcBuilding", "Unidad de proceso", "building")
    storey = root("IfcBuildingStorey", "Equipos", "storey")
    for parent, child in ((project, site), (site, building), (building, storey)):
        ifcopenshell.api.aggregate.assign_object(model, products=[child], relating_object=parent)

    def axis(origin=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0), reference=(1.0, 0.0, 0.0)):
        return model.create_entity(
            "IfcAxis2Placement3D",
            Location=model.create_entity("IfcCartesianPoint", Coordinates=origin),
            Axis=model.create_entity("IfcDirection", DirectionRatios=direction),
            RefDirection=model.create_entity("IfcDirection", DirectionRatios=reference),
        )

    def cylinder(
        product, diameter, length, origin=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0), thickness=None
    ):
        # Todas las longitudes entran en mm y se convierten una sola vez a metros.
        reference = (0.0, 0.0, 1.0) if direction[2] == 0.0 else (1.0, 0.0, 0.0)
        product.ObjectPlacement = model.create_entity(
            "IfcLocalPlacement", RelativePlacement=axis(origin, direction, reference)
        )
        profile_args = {"ProfileType": "AREA", "Radius": diameter / 2000}
        if thickness:
            profile_args["WallThickness"] = thickness / 1000
        profile = model.create_entity(
            "IfcCircleHollowProfileDef" if thickness else "IfcCircleProfileDef", **profile_args
        )
        solid = model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=axis(),
            ExtrudedDirection=model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
            Depth=length / 1000,
        )
        representation = model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[solid],
        )
        product.Representation = model.create_entity(
            "IfcProductDefinitionShape", Representations=[representation]
        )

    def pset(product, name, properties):
        prop_set = ifcopenshell.api.pset.add_pset(model, product=product, name=name)
        ifcopenshell.api.pset.edit_pset(model, pset=prop_set, properties=properties)

    equipment = revision.equipment
    key = f"equipment/{equipment.id}"
    tag = equipment.tag.value
    vessel = root("IfcTank", tag, key, predefined_type="PRESSUREVESSEL")
    vessel.Tag = tag
    cylinder(
        vessel,
        equipment.diameter.value,
        equipment.height.value,
        (0.0, 0.0, equipment.shell_bottom / 1000),
    )
    products = [vessel]
    pset(vessel, "TrazIA_Identity", {"ComponentId": "shell", "EquipmentId": equipment.id})
    for name, up, z in (
        ("bottom_head", -1, equipment.shell_bottom),
        ("top_head", 1, equipment.shell_bottom + equipment.height.value),
    ):
        product = root("IfcBuildingElementProxy", f"{tag}/{name}", f"{key}/{name}")
        product.Tag = name
        product.ObjectType = "ELLIPSOIDAL_HEAD"
        product.ObjectPlacement = model.create_entity("IfcLocalPlacement", RelativePlacement=axis())
        vertices, triangles = head_mesh(
            equipment.diameter.value / 2000, equipment.head_depth.value / 1000, z / 1000, up
        )
        face_set = model.create_entity(
            "IfcTriangulatedFaceSet",
            Coordinates=model.create_entity("IfcCartesianPointList3D", CoordList=vertices),
            Closed=True,
            CoordIndex=triangles,
        )
        representation = model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body,
            RepresentationIdentifier="Body",
            RepresentationType="Tessellation",
            Items=[face_set],
        )
        product.Representation = model.create_entity(
            "IfcProductDefinitionShape", Representations=[representation]
        )
        pset(product, "TrazIA_Identity", {"ComponentId": name, "EquipmentId": equipment.id})
        products.append(product)
    support = root("IfcBuildingElementProxy", f"{tag}/skirt", f"{key}/skirt")
    support.Tag = "skirt"
    support.ObjectType = "SKIRT_SUPPORT"
    cylinder(
        support,
        equipment.diameter.value,
        equipment.skirt_height.value,
        thickness=equipment.skirt_thickness.value,
    )
    pset(support, "TrazIA_Identity", {"ComponentId": "skirt", "EquipmentId": equipment.id})
    products.append(support)
    for nozzle in equipment.nozzles:
        product = root("IfcPipeSegment", f"{tag}/{nozzle.id}", f"{key}/nozzle/{nozzle.id}")
        product.Tag = nozzle.id
        angle = math.radians(nozzle.azimuth.value)
        direction = (math.cos(angle), math.sin(angle), 0.0)
        radius = equipment.diameter.value / 2000
        origin = (radius * direction[0], radius * direction[1], nozzle.elevation.value / 1000)
        cylinder(product, nozzle.diameter.value, nozzle.projection.value, origin, direction)
        pset(product, "TrazIA_Identity", {"EquipmentId": equipment.id, "ComponentId": nozzle.id})
        prefix = f"nozzles.{nozzle.id}."
        pset(
            product,
            "TrazIA_Traceability",
            {
                "FieldsJSON": json.dumps(
                    {
                        k: v.model_dump()
                        for k, v in fields(equipment).items()
                        if k.startswith(prefix)
                    },
                    ensure_ascii=False,
                ),
                "Revision": revision.revision,
                "Dataset": revision.dataset,
                "Draft": draft,
            },
        )
        products.append(product)
    ifcopenshell.api.spatial.assign_container(model, products=products, relating_structure=storey)
    model.create_entity(
        "IfcRelAssignsToProduct",
        GlobalId=stable_guid(f"{base}/{key}/components"),
        RelatedObjects=products[1:],
        RelatingProduct=vessel,
    )
    pset(
        vessel,
        "TrazIA_Traceability",
        {
            "Revision": revision.revision,
            "Dataset": revision.dataset,
            "Draft": draft,
            "EquipmentId": equipment.id,
            "LengthUnitInput": "mm",
            "InputSHA256": revision.fingerprint(),
            "ApprovalJSON": revision.approval.model_dump_json() if revision.approval else "",
            "DocumentsJSON": json.dumps(
                [d.model_dump() for d in revision.documents], ensure_ascii=False
            ),
            "FieldsJSON": json.dumps(
                {k: v.model_dump() for k, v in fields(equipment).items()}, ensure_ascii=False
            ),
        },
    )
    for component in products[1:4]:
        pset(
            component,
            "TrazIA_Traceability",
            {
                "Revision": revision.revision,
                "Dataset": revision.dataset,
                "Draft": draft,
                "InputSHA256": revision.fingerprint(),
                "FieldsJSON": json.dumps(
                    {
                        k: v.model_dump(mode="json")
                        for k, v in fields(equipment).items()
                        if k
                        in ("diameter", "head_depth", "height", "skirt_height", "skirt_thickness")
                    },
                    ensure_ascii=False,
                ),
            },
        )
    if equipment.attributes:
        pset(
            vessel,
            "TrazIA_Technical",
            {k: f"{v.value} {v.unit}" for k, v in equipment.attributes.items()},
        )
    return model


def export_ifc(revision: Revision, destination: Path, *, draft: bool = False) -> Path:
    model = build_ifc(revision, draft=draft)
    destination.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(destination))
    return destination


def head_mesh(radius: float, depth: float, z: float, up: int, segments=64, rings=12):
    """Semielipsoide macizo cerrado; aproximación de la envolvente exterior en metros."""
    vertices, triangles = [], []
    for row in range(rings):
        angle = math.pi * row / (2 * rings)
        r = radius * math.cos(angle)
        for col in range(segments):
            theta = 2 * math.pi * col / segments
            vertices.append(
                (r * math.cos(theta), r * math.sin(theta), z + up * depth * math.sin(angle))
            )
    pole = len(vertices) + 1
    vertices.append((0.0, 0.0, z + up * depth))
    center = len(vertices) + 1
    vertices.append((0.0, 0.0, z))
    for row in range(rings - 1):
        for col in range(segments):
            a = row * segments + col + 1
            b = row * segments + (col + 1) % segments + 1
            triangles.extend(((a, b, b + segments), (a, b + segments, a + segments)))
    for col in range(segments):
        nxt = (col + 1) % segments
        triangles.append(((rings - 1) * segments + col + 1, (rings - 1) * segments + nxt + 1, pole))
        triangles.append((center, nxt + 1, col + 1))
    if up < 0:
        triangles = [tuple(reversed(t)) for t in triangles]
    return vertices, triangles
