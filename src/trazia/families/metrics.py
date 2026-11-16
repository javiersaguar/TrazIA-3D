"""Distancias reproducibles de superficies IFC, en metros (requiere extra geo)."""

from pathlib import Path

import numpy as np

from ..viewer import meshes_from_ifc


def bbox_iou(a, b):
    amin, amax = np.asarray(a).min(axis=0), np.asarray(a).max(axis=0)
    bmin, bmax = np.asarray(b).min(axis=0), np.asarray(b).max(axis=0)
    intersection = np.prod(np.maximum(0, np.minimum(amax, bmax) - np.maximum(amin, bmin)))
    union = np.prod(amax - amin) + np.prod(bmax - bmin) - intersection
    return float(intersection / union) if union > 0 else 0.0


def _distance_to_surface(mesh, points):
    """Distancia de cada punto a la malla: lo mismo que `trimesh.proximity.closest_point(...)[1]`.

    Mismo método (vértice más cercano → caja → triángulos candidatos del mismo rtree → punto más
    cercano de cada triángulo, con el desempate de trimesh entre dos caras), pero la consulta
    al rtree va en bloque (`intersection_v`) y la selección de los dos mejores es vectorial:
    sin bucles Python por punto. Medido el 16/11/2026 con el IFC rev A/B de la demo (73 piezas):
    misma salida bit a bit y `compare-ifc` pasa de 10,3 s a 5,6 s.
    """
    import trimesh
    from scipy.spatial import cKDTree
    from trimesh.constants import tol
    from trimesh.triangles import closest_point as closest_on_triangles
    from trimesh.util import diagonal_dot

    points = np.asarray(points, dtype=np.float64)
    reach = cKDTree(mesh.vertices[mesh.referenced_vertices]).query(points)[0].reshape((-1, 1))
    reach += tol.merge
    ids, counts = mesh.triangles_tree.intersection_v(points - reach, points + reach)
    ids, counts = np.asarray(ids, dtype=np.int64), np.asarray(counts, dtype=np.int64)
    if len(counts) != len(points) or not counts.all():
        return trimesh.proximity.closest_point(mesh, points)[1]  # caso límite: el de siempre
    owner = np.repeat(np.arange(len(points)), counts)
    query = points[owner]
    vector = query - closest_on_triangles(mesh.triangles.view(np.ndarray)[ids], query)
    squared = diagonal_dot(vector, vector)
    # Los dos candidatos más cercanos de cada punto (con uno solo, se repite como en trimesh).
    order = np.lexsort((squared, owner))
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    two = order[np.column_stack((starts, np.where(counts > 1, starts + 1, starts)))]
    two_squared = squared[two]
    result = two_squared[:, 0].copy()
    tie = (np.ptp(two_squared, axis=1) < tol.merge) & np.all(
        np.abs(two_squared) > tol.merge, axis=1
    )
    if tie.any():
        normals = mesh.face_normals[ids[two[tie]]]
        vectors = vector[two[tie]] / two_squared[tie].reshape(-1, 2, 1) ** 0.5
        pick = (normals * vectors).sum(axis=2).argmax(axis=1)
        result[tie] = two_squared[tie][np.arange(len(pick)), pick]
    return result**0.5


def surface_distances(before, after, *, samples=1024, seed=2026):
    """Hausdorff aproximado y Chamfer no cuadrático: muestras → triángulos, no cajas.

    Se incluyen vértices y centroides además del muestreo por área. El máximo observado
    es una cota inferior de Hausdorff continuo, no una garantía de error geométrico máximo.
    Los arrays por vértice permiten pintar un mapa de error sin reconstruir geometría.
    """
    import trimesh

    if not 16 <= samples <= 100_000:
        raise ValueError("samples debe estar entre 16 y 100000")

    def mesh(value):
        vertices = np.asarray(value["vertices"], dtype=float).reshape(-1, 3)
        faces = np.asarray(value["faces"], dtype=int).reshape(-1, 3)
        if not len(vertices) or not len(faces):
            raise ValueError("La comparación necesita superficies trianguladas no vacías")
        if not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
            raise ValueError("Malla inválida")
        return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    left, right = mesh(before), mesh(after)

    def sample(value):
        points, _ = trimesh.sample.sample_surface(value, samples, seed=seed)
        return np.vstack((value.vertices, value.triangles_center, points))

    lr = _distance_to_surface(right, sample(left))
    rl = _distance_to_surface(left, sample(right))
    vertex_error = _distance_to_surface(right, left.vertices)
    return {
        "unit": "m",
        "method": "area-sampling-to-triangles",
        "seed": seed,
        "samples_per_surface": samples,
        "hausdorff_sampled": float(max(lr.max(), rl.max())),
        "chamfer": float((lr.mean() + rl.mean()) / 2),
        "bbox_iou": bbox_iou(left.vertices, right.vertices),
        "before_vertex_distances": vertex_error.tolist(),
        "hausdorff_is_continuous_bound": False,
    }


def compare_ifc(before: str | Path, after: str | Path, *, samples=1024, seed=2026, match="guid"):
    def content(value):
        return value.read_text(encoding="utf-8") if isinstance(value, Path) else value

    if match not in ("guid", "name"):
        raise ValueError("match debe ser guid o name")
    key = "guid" if match == "guid" else "name"

    def index(value):
        meshes = meshes_from_ifc(content(value))
        indexed = {m[key]: m for m in meshes}
        if len(indexed) != len(meshes):
            raise ValueError(f"Correspondencia ambigua: {key} duplicado en IFC")
        return indexed

    old, new = index(before), index(after)
    elements = []
    for guid in sorted(old.keys() | new.keys()):
        a, b = old.get(guid), new.get(guid)
        if a is None or b is None:
            elements.append(
                {
                    "guid": (b or a)["guid"],
                    "name": (b or a)["name"],
                    "operation": "added" if a is None else "removed",
                }
            )
        else:
            elements.append(
                {
                    "guid": (b or a)["guid"],
                    "name": b["name"],
                    "operation": "compared",
                    **surface_distances(a, b, samples=samples, seed=seed),
                }
            )
    return {
        "unit": "m",
        "elements": elements,
        "matched_by": "GlobalId" if match == "guid" else "Name (exacto y único)",
        "seed": seed,
    }
