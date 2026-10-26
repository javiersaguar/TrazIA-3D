"""Semántica IFC y documentos; no modifica el contrato ni declara aprobaciones automáticas."""

import json
from datetime import timezone

import ifcopenshell.api.owner

from ..model import fields
from . import nozzle_frame


def initialize_owner(model):
    # Registros locales por archivo: no se sobrescriben callbacks globales entre hilos.
    organization = ifcopenshell.api.owner.add_organisation(
        model, identification="TrazIA-3D", name="TrazIA-3D"
    )
    person = ifcopenshell.api.owner.add_person(
        model, identification="local-export", family_name="Exportación local"
    )
    ifcopenshell.api.owner.add_person_and_organisation(
        model, person=person, organisation=organization
    )
    ifcopenshell.api.owner.add_application(
        model,
        application_developer=organization,
        version="0.3",
        application_full_name="TrazIA-3D",
        application_identifier="TRAZIA",
    )


def enrich(model, revision, products, *, draft, pset, axis, guid):
    equipment = revision.equipment
    vessel = products[0]
    base = f"{revision.project_id}/equipment/{equipment.id}"
    owner = vessel.OwnerHistory

    def relation(ifc_class, key, **kwargs):
        return model.create_entity(
            ifc_class, GlobalId=guid(f"{base}/{key}"), OwnerHistory=owner, **kwargs
        )

    common = {
        "pump": "Pset_PumpTypeCommon",
        "compressor": "Pset_CompressorTypeCommon",
        "generic": "Pset_BuildingElementProxyCommon",
    }.get(equipment.kind, "Pset_TankTypeCommon")
    pset(vessel, common, {"Reference": equipment.tag.value})
    all_fields = fields(equipment)
    pset(
        vessel,
        "TrazIA_Provenance",
        {
            "InputSHA256": revision.fingerprint(),
            "SchemaVersion": revision.schema_version,
            "Revision": revision.revision,
            "Dataset": revision.dataset,
            "Draft": draft,
            "LOD": equipment.lod,
            "Family": equipment.kind,
            "RunJSON": revision.run.model_dump_json() if revision.run else "",
            "DocumentsSHA256": json.dumps(
                {d.id: d.sha256 for d in revision.documents}, sort_keys=True
            ),
            "SourcesJSON": json.dumps(
                {p: f.source.model_dump(mode="json") for p, f in all_fields.items()},
                ensure_ascii=False,
            ),
        },
    )
    for document in revision.documents:
        args = {"Location": f"urn:sha256:{document.sha256}", "Name": document.filename}
        args["ItemReference" if model.schema == "IFC2X3" else "Identification"] = document.sha256
        reference = model.create_entity("IfcDocumentReference", **args)
        relation(
            "IfcRelAssociatesDocument",
            f"document/{document.id}",
            RelatedObjects=products,
            RelatingDocument=reference,
        )
    by_name = {p.Name: p for p in products}
    for nozzle in equipment.nozzles:
        origin, direction = nozzle_frame(equipment, nozzle)
        distance = nozzle.projection.value / 1000
        endpoint = tuple(p + distance * d for p, d in zip(origin, direction))
        port = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcDistributionPort", name=f"{equipment.tag.value}/{nozzle.id}/port"
        )
        port.GlobalId = guid(f"{base}/nozzle/{nozzle.id}/port")
        port.FlowDirection = "NOTDEFINED"
        if model.schema != "IFC2X3":
            port.PredefinedType = "PIPE"
            port.SystemType = "NOTDEFINED"
        # Coordenadas globales, como las boquillas. La relación semántica no las recalcula.
        port.ObjectPlacement = model.create_entity(
            "IfcLocalPlacement", RelativePlacement=axis(endpoint, direction)
        )
        product = by_name[f"{equipment.tag.value}/{nozzle.id}"]
        if model.schema == "IFC2X3":
            relation(
                "IfcRelConnectsPortToElement",
                f"nozzle/{nozzle.id}/port/attachment",
                RelatingPort=port,
                RelatedElement=product,
            )
        else:
            relation(
                "IfcRelNests",
                f"nozzle/{nozzle.id}/port/attachment",
                RelatingObject=product,
                RelatedObjects=[port],
            )
        pset(
            product,
            "Pset_PipeSegmentTypeCommon",
            {"Reference": nozzle.id, "NominalDiameter": nozzle.diameter.value / 1000},
        )
        pset(
            product,
            "TrazIA_Provenance",
            {
                "PortGUID": port.GlobalId,
                "InputSHA256": revision.fingerprint(),
                "Draft": draft,
                "Service": str(nozzle.service.value) if nozzle.service else "",
                "Rating": str(nozzle.rating.value) if nozzle.rating else "",
            },
        )
    if not draft and revision.approval:
        approval = revision.approval
        stamp = approval.timestamp.astimezone(timezone.utc)
        description = (
            f"Revisión humana declarada por {approval.reviewer}; SHA-256 {approval.input_sha256}"
        )
        if model.schema == "IFC2X3":
            date = model.create_entity(
                "IfcCalendarDate",
                DayComponent=stamp.day,
                MonthComponent=stamp.month,
                YearComponent=stamp.year,
            )
            zone = model.create_entity(
                "IfcCoordinatedUniversalTimeOffset", HourOffset=0, Sense="AHEAD"
            )
            clock = model.create_entity(
                "IfcLocalTime",
                HourComponent=stamp.hour,
                MinuteComponent=stamp.minute,
                SecondComponent=float(stamp.second),
                Zone=zone,
            )
            date_time = model.create_entity(
                "IfcDateAndTime", DateComponent=date, TimeComponent=clock
            )
            entity = model.create_entity(
                "IfcApproval",
                Name=approval.reviewer,
                Identifier=approval.input_sha256,
                Description=description,
                ApprovalDateTime=date_time,
                ApprovalStatus="APPROVED",
                ApprovalLevel="HUMAN_REVIEW",
            )
        else:
            entity = model.create_entity(
                "IfcApproval",
                Name=approval.reviewer,
                Identifier=approval.input_sha256,
                Description=description,
                TimeOfApproval=stamp.isoformat(),
                Status="APPROVED",
                Level="HUMAN_REVIEW",
            )
        relation(
            "IfcRelAssociatesApproval", "approval", RelatedObjects=products, RelatingApproval=entity
        )
