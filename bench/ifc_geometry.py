"""Geometría por elemento leída de un IFC: la misma función sirve para nuestro IFC y para el
IFC de referencia de Técnicas Reunidas (ROADMAP G.1). Coordenadas devueltas en mm."""

import ifcopenshell
import ifcopenshell.geom

from .metrics import box_center, box_iou, distance


def element_boxes(model: ifcopenshell.file) -> dict[str, tuple]:
    """Caja envolvente en mm de cada elemento, indexada por nombre de componente.

    Para los IFC de TrazIA el nombre es «TAG/componente» y el tanque se llama como el tag; se
    normaliza a shell, top_head, bottom_head, skirt, N1… Para IFC externos habrá que añadir aquí
    la correspondencia de nombres cuando se conozca el dataset.
    """
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    boxes = {}
    for product in model.by_type("IfcElement"):
        if not product.Representation:
            continue
        shape = ifcopenshell.geom.create_shape(settings, product)
        verts = shape.geometry.verts
        xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
        name = product.Name or product.GlobalId
        key = name.split("/", 1)[1] if "/" in name else "shell"
        boxes[key] = (
            (min(xs) * 1000, min(ys) * 1000, min(zs) * 1000),
            (max(xs) * 1000, max(ys) * 1000, max(zs) * 1000),
        )
    return boxes


def compare_models(predicted: ifcopenshell.file, reference: ifcopenshell.file) -> dict:
    """Compara elemento a elemento: presencia, distancia entre centros (mm) e IoU de cajas."""
    ours, ref = element_boxes(predicted), element_boxes(reference)
    rows = []
    for name, box in ref.items():
        mine = ours.get(name)
        rows.append(
            {
                "element": name,
                "found": mine is not None,
                "center_error_mm": distance(box_center(mine), box_center(box)) if mine else None,
                "iou": box_iou(mine, box) if mine else 0.0,
            }
        )
    extra = sorted(set(ours) - set(ref))
    return {"elements": rows, "extra": extra}
