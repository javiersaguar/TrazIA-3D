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

    _, lr, _ = trimesh.proximity.closest_point(right, sample(left))
    _, rl, _ = trimesh.proximity.closest_point(left, sample(right))
    _, vertex_error, _ = trimesh.proximity.closest_point(right, left.vertices)
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
