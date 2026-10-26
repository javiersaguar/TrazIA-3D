import json
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

from .families import Solid, parts
from .families.geometry import head_mesh  # API histórica usada en pruebas geométricas.
from .model import Revision, fields

__all__ = ["build_ifc", "export_ifc", "head_mesh", "stable_guid"]


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

    def axis(origin=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0)):
        # Elegir una referencia perpendicular también para boquillas inclinadas.
        seed = (0.0, 0.0, 1.0) if abs(direction[2]) < 0.9 else (1.0, 0.0, 0.0)
        dot = sum(a * b for a, b in zip(seed, direction))
        reference = tuple(a - dot * b for a, b in zip(seed, direction))
        return model.create_entity(
            "IfcAxis2Placement3D",
            Location=model.create_entity("IfcCartesianPoint", Coordinates=origin),
            Axis=model.create_entity("IfcDirection", DirectionRatios=direction),
            RefDirection=model.create_entity("IfcDirection", DirectionRatios=reference),
        )

    def swept(profile, depth):
        return model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=axis(),
            ExtrudedDirection=model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
            Depth=depth,
        )

    def solid_item(solid: Solid):
        if solid.kind == "mesh":
            return model.create_entity(
                "IfcTriangulatedFaceSet",
                Coordinates=model.create_entity(
                    "IfcCartesianPointList3D", CoordList=solid.vertices
                ),
                Closed=True,
                CoordIndex=solid.triangles,
            ), "Tessellation"
        if solid.kind == "cylinder":
            args = {"ProfileType": "AREA", "Radius": solid.diameter / 2000}
            if solid.thickness:
                args["WallThickness"] = solid.thickness / 1000
            profile = model.create_entity(
                "IfcCircleHollowProfileDef" if solid.thickness else "IfcCircleProfileDef", **args
            )
            return swept(profile, solid.length / 1000), "SweptSolid"
        if solid.kind == "box":
            x, y, z = solid.size
            profile = model.create_entity(
                "IfcRectangleProfileDef",
                ProfileType="AREA",
                XDim=x,
                YDim=y,
                Position=model.create_entity(
                    "IfcAxis2Placement2D",
                    Location=model.create_entity("IfcCartesianPoint", Coordinates=(x / 2, y / 2)),
                ),
            )
            return swept(profile, z), "SweptSolid"
        if solid.kind == "profile":
            # El eje X global es la extrusión; X/Y locales son Y/Z globales.
            polyline = model.create_entity(
                "IfcPolyline",
                Points=[
                    model.create_entity("IfcCartesianPoint", Coordinates=p)
                    for p in (*solid.points, solid.points[0])
                ],
            )
            profile = model.create_entity(
                "IfcArbitraryClosedProfileDef", ProfileType="AREA", OuterCurve=polyline
            )
            return swept(profile, solid.length / 1000), "SweptSolid"
        raise ValueError(f"Sólido desconocido: {solid.kind}")

    def represent(product, solids):
        items = []
        for solid in solids:
            item, kind = solid_item(solid)
            if len(solids) == 1:
                placement = axis(solid.origin, solid.direction)
                if solid.kind == "profile":
                    placement.RefDirection = model.create_entity(
                        "IfcDirection", DirectionRatios=(0.0, 1.0, 0.0)
                    )
                product.ObjectPlacement = model.create_entity(
                    "IfcLocalPlacement", RelativePlacement=placement
                )
            else:
                item.Position = axis(solid.origin, solid.direction)
            items.append(item)
        if len(solids) > 1:
            product.ObjectPlacement = model.create_entity(
                "IfcLocalPlacement", RelativePlacement=axis()
            )
        representation = model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=body,
            RepresentationIdentifier="Body",
            RepresentationType=kind,
            Items=items,
        )
        product.Representation = model.create_entity(
            "IfcProductDefinitionShape", Representations=[representation]
        )

    def pset(product, name, properties):
        p = ifcopenshell.api.pset.add_pset(model, product=product, name=name)
        ifcopenshell.api.pset.edit_pset(model, pset=p, properties=properties)

    equipment = revision.equipment
    key = f"equipment/{equipment.id}"
    tag = equipment.tag.value
    classes = {
        "pump": "IfcPump",
        "compressor": "IfcCompressor",
        "generic": "IfcBuildingElementProxy",
    }
    main_class = classes.get(equipment.kind, "IfcTank")
    vessel = root(
        main_class,
        tag,
        key,
        predefined_type="PRESSUREVESSEL"
        if main_class == "IfcTank" and equipment.kind != "tank"
        else "NOTDEFINED",
    )
    vessel.Tag = tag
    products = []
    traced = fields(equipment)
    for index, part in enumerate(parts(equipment)):
        product = (
            vessel
            if index == 0
            else root(part.ifc_class, f"{tag}/{part.id}", f"{key}/{part.guid_key}")
        )
        if index > 0:
            product.Tag = part.id
            product.ObjectType = part.object_type
        represent(product, part.solids)
        pset(product, "TrazIA_Identity", {"ComponentId": part.id, "EquipmentId": equipment.id})
        prefix = f"nozzles.{part.id}."
        local_fields = (
            traced
            if index == 0
            else {
                k: v
                for k, v in traced.items()
                if k.startswith(prefix) or not k.startswith("nozzles.")
            }
        )
        pset(
            product,
            "TrazIA_Traceability",
            {
                "Revision": revision.revision,
                "Dataset": revision.dataset,
                "Draft": draft,
                "LOD": equipment.lod,
                "Family": equipment.kind,
                "EquipmentId": equipment.id,
                "LengthUnitInput": "mm",
                "InputSHA256": revision.fingerprint(),
                "FieldsJSON": json.dumps(
                    {k: v.model_dump(mode="json") for k, v in local_fields.items()},
                    ensure_ascii=False,
                ),
            },
        )
        products.append(product)
    ifcopenshell.api.spatial.assign_container(model, products=products, relating_structure=storey)
    if len(products) > 1:
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
            "ApprovalJSON": revision.approval.model_dump_json() if revision.approval else "",
            "DocumentsJSON": json.dumps(
                [d.model_dump() for d in revision.documents], ensure_ascii=False
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
