"""Comparación física, identidad de boquillas y diferencias visuales; nunca aprueba datos."""

import hashlib
import math

import numpy as np

from ..model import Revision
from . import nozzle_frame

# Por debajo de esto es ruido de lectura, no cambio de diseño (ROADMAP F.2): medir sobre los trazos
# o convertir pulgadas deja diferencias de décimas de milímetro entre revisiones.
LENGTH_TOLERANCE_MM = 1.0
ANGLE_TOLERANCE_DEG = 0.5


def equal_value(left, right, path, *, tolerances=None):
    if left is None or right is None:
        return left is right
    if isinstance(left.value, str) or isinstance(right.value, str):
        return (left.value, left.unit) == (right.value, right.unit)
    value = float(right.value)
    if left.unit != right.unit:
        try:
            import pint

            registry = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

            def unit(text):
                if text == "C" and "temperature" in path:
                    return "degC"
                if text in ("kg/cm2", "kg/cm²") and "pressure" in path:
                    return "kgf/cm**2"
                return text

            value = registry.Quantity(value, unit(right.unit)).to(unit(left.unit)).magnitude
        except (ImportError, ValueError, TypeError, AttributeError):
            return False
    tolerance = (tolerances or {}).get(
        path,
        LENGTH_TOLERANCE_MM
        if left.unit == "mm"
        else ANGLE_TOLERANCE_DEG
        if left.unit == "deg"
        else 0.0,
    )
    distance = abs(left.value - value)
    if left.unit == "deg":
        distance = min(distance % 360, 360 - distance % 360)
    return distance <= max(tolerance, abs(left.value) * 1e-9)


def match_nozzles(before, after, *, threshold=0.75, margin=0.12):
    matches = []
    for old in before.nozzles:
        new = next(
            (n for n in after.nozzles if (n.stable_id or n.id) == (old.stable_id or old.id)), None
        )
        if new is not None:
            matches.append(
                {
                    "before_id": old.id,
                    "after_id": new.id,
                    "method": "stable-id",
                    "cost": 0.0,
                    "ambiguous": False,
                }
            )
    left = [n for n in before.nozzles if not any(m["before_id"] == n.id for m in matches)]
    right = [n for n in after.nozzles if not any(m["after_id"] == n.id for m in matches)]
    if not left or not right:
        return matches
    from scipy.optimize import linear_sum_assignment

    n, m = len(left), len(right)
    costs = np.zeros((n + m, n + m))
    costs[:n, m:] = threshold / 2
    costs[n:, :m] = threshold / 2
    for i, a in enumerate(left):
        pa, da = nozzle_frame(before, a)
        for j, b in enumerate(right):
            pb, db = nozzle_frame(after, b)
            diameter = abs(a.diameter.value - b.diameter.value) / max(
                a.diameter.value, b.diameter.value
            )
            position = min(3, math.dist(pa, pb))
            service = (
                0.15
                if not a.service or not b.service
                else float(str(a.service.value).casefold() != str(b.service.value).casefold())
            )
            direction = 1 - sum(x * y for x, y in zip(da, db))
            costs[i, j] = 0.5 * diameter + 0.35 * position + service + 0.15 * direction
            if a.stable_id and b.stable_id and a.stable_id != b.stable_id:
                costs[i, j] = threshold * 2
    rows, cols = linear_sum_assignment(costs)
    for i, j in zip(rows, cols):
        if i >= n or j >= m or costs[i, j] >= threshold:
            continue
        alternatives = [costs[i, k] for k in range(m) if k != j] + [
            costs[k, j] for k in range(n) if k != i
        ]
        ambiguous = bool(alternatives and min(alternatives) - costs[i, j] < margin)
        matches.append(
            {
                "before_id": left[i].id,
                "after_id": right[j].id,
                "method": "hungarian-service-diameter-position",
                "cost": float(costs[i, j]),
                "ambiguous": ambiguous,
            }
        )
    return matches


def preserve_nozzle_identity(before, after):
    """Copia DRAFT; solo propaga identidad cuando el emparejamiento no es ambiguo."""
    result = after.model_copy(deep=True)
    result.approval = None
    for match in match_nozzles(before.equipment, result.equipment):
        if match["ambiguous"]:
            continue
        old = next(n for n in before.equipment.nozzles if n.id == match["before_id"])
        new = next(n for n in result.equipment.nozzles if n.id == match["after_id"])
        stable = old.stable_id or old.id
        if new.stable_id and new.stable_id != stable:
            raise ValueError("La identidad propuesta contradice el stable_id de la boquilla")
        if old.id != new.id or old.stable_id:
            new.stable_id = stable
    return Revision.model_validate_json(result.model_dump_json())


def geometry_delta(before, after, *, tolerance_mm=0.1):
    from scipy.spatial import cKDTree

    from ..ifc import build_ifc
    from ..viewer import meshes_from_ifc
    from .metrics import bbox_iou

    if tolerance_mm < 0:
        raise ValueError("La tolerancia debe ser no negativa")

    def meshes(revision):
        return {m["guid"]: m for m in meshes_from_ifc(build_ifc(revision).to_string())}

    old, new = meshes(before), meshes(after)
    elements = []
    for guid in sorted(old.keys() | new.keys()):
        a, b = old.get(guid), new.get(guid)
        if a is None or b is None:
            elements.append(
                {
                    "guid": guid,
                    "name": (b or a)["name"],
                    "operation": "added" if a is None else "removed",
                }
            )
            continue
        x = np.asarray(a["vertices"]).reshape(-1, 3)
        y = np.asarray(b["vertices"]).reshape(-1, 3)
        distance = float(max(cKDTree(x).query(y)[0].max(), cKDTree(y).query(x)[0].max()))
        if distance > tolerance_mm / 1000:
            elements.append(
                {
                    "guid": guid,
                    "name": b["name"],
                    "operation": "modified",
                    "vertex_hausdorff_m": distance,
                    "bbox_iou": bbox_iou(x, y),
                }
            )
    return {
        "status": "ok",
        "method": "world-mesh-vertices-by-guid",
        "tolerance_mm": tolerance_mm,
        "elements": elements,
        "detail": "Vértices por GUID; distancia de superficie disponible en compare-ifc.",
    }


def render_pdf(data, page=1):
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        if not 1 <= page <= len(document):
            raise ValueError("Página fuera del PDF")
        source = document[page - 1]
        try:
            scale = min(1.5, 1000 / max(source.get_size()))
            bitmap = source.render(scale=scale)
            try:
                return np.asarray(bitmap.to_pil().convert("RGB")).copy()
            finally:
                bitmap.close()
        finally:
            source.close()
    finally:
        document.close()


def _align_box(box, page):
    if "warp" not in page or "width" not in page:
        return box
    width, height = page["width"], page["height"]
    matrix = np.vstack((np.asarray(page["warp"]), (0.0, 0.0, 1.0)))
    x0, y0, x1, y1 = box
    corners = np.array(
        [
            [x0 * width, y0 * height, 1],
            [x1 * width, y0 * height, 1],
            [x1 * width, y1 * height, 1],
            [x0 * width, y1 * height, 1],
        ]
    )
    aligned = corners @ np.linalg.inv(matrix).T
    xs, ys = aligned[:, 0] / width, aligned[:, 1] / height
    return [
        float(max(0, xs.min())),
        float(max(0, ys.min())),
        float(min(1, xs.max())),
        float(min(1, ys.max())),
    ]


def visual_diff_images(before, after, *, return_png=False):
    import cv2

    a = cv2.cvtColor(before, cv2.COLOR_RGB2GRAY)
    b = cv2.cvtColor(after, cv2.COLOR_RGB2GRAY)
    if a.shape != b.shape:
        return {
            "status": "unaligned",
            "detail": "Las páginas tienen tamaños distintos; revisar correspondencia",
        }, None
    height, width = a.shape
    warp = np.eye(2, 3, dtype=np.float32)
    if np.array_equal(a, b):
        score = 1.0
    else:
        try:
            score, warp = cv2.findTransformECC(
                a.astype(np.float32) / 255,
                b.astype(np.float32) / 255,
                warp,
                cv2.MOTION_EUCLIDEAN,
                (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 100, 1e-5),
                None,
                5,
            )
        except cv2.error:
            return {
                "status": "unaligned",
                "detail": "ECC no converge; no se atribuyen cambios a píxeles sin alinear",
            }, None
    rotation = abs(math.degrees(math.atan2(warp[1, 0], warp[0, 0])))
    if (
        score < 0.5
        or rotation > 3
        or abs(warp[0, 2]) > 0.05 * width
        or abs(warp[1, 2]) > 0.05 * height
    ):
        return {
            "status": "unaligned",
            "detail": "Alineación fuera de límites (3 grados/5 % de página)",
        }, None
    aligned = cv2.warpAffine(
        b, warp, (width, height), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=255
    )
    valid = cv2.warpAffine(
        np.ones_like(b), warp, (width, height), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP
    )
    valid = cv2.erode(valid, np.ones((3, 3), np.uint8)) > 0
    mask = ((cv2.absdiff(a, aligned) > 30) & valid).astype(np.uint8) * 255
    clustered = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(clustered)
    regions = []
    for x, y, w, h, area in stats[1:count]:
        if area >= 8:
            regions.append(
                [
                    float(x / width),
                    float(y / height),
                    float((x + w) / width),
                    float((y + h) / height),
                ]
            )
    regions = sorted(regions, key=lambda r: -(r[2] - r[0]) * (r[3] - r[1]))
    # Marcadores candidatos: triángulos y contornos festoneados; nunca lectura certificada.
    contours, _ = cv2.findContours(
        (b < 100).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )
    markers = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not 30 <= area <= 0.05 * width * height:
            continue
        perimeter = cv2.arcLength(contour, True)
        poly = cv2.approxPolyDP(contour, 0.035 * perimeter, True)
        kind = None
        if len(poly) == 3 and area < 0.005 * width * height:
            kind = "delta_triangle_candidate"
        elif len(contour) >= 12:
            hull = cv2.convexHull(contour, returnPoints=False)
            if len(hull) >= 3:
                try:
                    defects = cv2.convexityDefects(contour, hull)
                except cv2.error:
                    defects = None
                if defects is not None and sum(d[0][3] > 1.5 * 256 for d in defects) >= 6:
                    kind = "revision_cloud_candidate"
        if kind:
            x, y, w, h = cv2.boundingRect(contour)
            markers.append(
                {
                    "kind": kind,
                    "bbox": [x / width, y / height, (x + w) / width, (y + h) / height],
                    "method": "heuristic",
                }
            )
    frame = {"warp": warp.tolist(), "width": width, "height": height}
    markers = [{**marker, "bbox": _align_box(marker["bbox"], frame)} for marker in markers]
    image = None
    if return_png:
        overlay = cv2.cvtColor(aligned, cv2.COLOR_GRAY2BGR)
        overlay[mask > 0] = (40, 50, 230)
        ok, encoded = cv2.imencode(".png", overlay)
        if ok:
            image = encoded.tobytes()
    return {
        "status": "ok",
        "method": "opencv-ecc-euclidean",
        "correlation": float(score),
        "warp": warp.tolist(),
        "width": width,
        "height": height,
        "coordinate_frame": "before-page",
        "regions": regions[:200],
        "regions_truncated": len(regions) > 200,
        "changed_pixel_fraction": float(np.count_nonzero(mask) / max(1, np.count_nonzero(valid))),
        "markers": markers[:200],
    }, image


def visual_delta(before, after, originals):
    import pypdfium2 as pdfium

    pages = []
    old = {d.id: d for d in before.documents}
    new = {d.id: d for d in after.documents}
    for identity in sorted(old.keys() & new.keys()):
        a, b = old[identity], new[identity]
        if not a.filename.lower().endswith(".pdf") or not b.filename.lower().endswith(".pdf"):
            continue
        first, second = originals.get(a.sha256), originals.get(b.sha256)
        if first is None or second is None:
            pages.append({"document_id": identity, "status": "missing_original"})
            continue
        if (
            hashlib.sha256(first).hexdigest() != a.sha256
            or hashlib.sha256(second).hexdigest() != b.sha256
        ):
            pages.append({"document_id": identity, "status": "hash_mismatch"})
            continue
        x = pdfium.PdfDocument(first)
        y = pdfium.PdfDocument(second)
        try:
            na, nb = len(x), len(y)
        finally:
            x.close()
            y.close()
        for page in range(1, min(max(na, nb), 10) + 1):
            if page > min(na, nb):
                result = {
                    "status": "ok",
                    "operation": "added" if page > na else "removed",
                    "regions": [[0, 0, 1, 1]],
                    "markers": [],
                }
            else:
                result, _ = visual_diff_images(render_pdf(first, page), render_pdf(second, page))
            pages.append({"document_id": identity, "page": page, **result})
    return {
        "status": "ok"
        if pages and all(p["status"] == "ok" for p in pages)
        else "partial"
        if any(p["status"] == "ok" for p in pages)
        else "not_available",
        "pages": pages,
        "page_limit_per_document": 10,
        "detail": "Marcadores heurísticos; ausencia de nube no prueba ausencia de cambio.",
    }


def crosscheck(changes, visual):
    def overlap(a, b):
        return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])

    suspects = []
    for page in visual.get("pages", []):
        if page.get("status") != "ok":
            continue
        associated = []
        for change in changes:
            source = change.get("after_source") or change.get("before_source") or {}
            if source.get("document_id") != page["document_id"] or source.get("page") != page.get(
                "page"
            ):
                continue
            box = source.get("bbox")
            if box is None:
                continue
            if change.get("after_source"):
                box = _align_box(box, page)
            hits = [r for r in page.get("regions", []) if overlap(box, r)]
            markers = [m for m in page.get("markers", []) if overlap(box, m["bbox"])]
            if not hits:
                suspects.append(
                    {
                        "kind": "field_without_visual_region",
                        "path": change["path"],
                        "document_id": page["document_id"],
                        "page": page.get("page"),
                        "detail": "Campo sin región visual; revisar evidencia.",
                    }
                )
            associated.extend(hits)
            change["revision_markers"] = markers
        for region in page.get("regions", []):
            if region not in associated:
                suspects.append(
                    {
                        "kind": "visual_region_without_field",
                        "document_id": page["document_id"],
                        "page": page.get("page"),
                        "bbox": region,
                        "detail": "Región sin campo asociado; revisar el documento.",
                    }
                )
    return suspects
