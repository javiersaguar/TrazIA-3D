"""Evaluación de un lote contra los IFC de referencia de Técnicas Reunidas (G.1, G.3, G.4 y G.5).

    uv run python -m bench.evaluar <salida del lote> <carpeta con los IFC de TR> [--mapas DIR]

Toma la salida de `trazia lote` (o del notebook `01_procesar_lote`) y, para cada equipo con un
IFC de referencia cuyo nombre contiene su tag, compara la última revisión correcta:

- dimensiones principales y boquillas con `bench.referencia` (por geometría, sin suponer nombres);
- convenio de azimut ajustado en el propio equipo y, si hay más equipos, por **exclusión de uno**
  (el convenio más frecuente en los demás): esa es la cifra defendible;
- superficie completa: los dos IFC se llevan al mismo marco (eje del cuerpo y cota más baja) y se
  mide la distancia entre superficies en mm (Hausdorff muestreado, percentil 95 y Chamfer);
- mapa de calor 3D opcional (HTML de Plotly): nuestro modelo coloreado por su distancia a la
  referencia, con la referencia en gris translúcido.

Con datos de TR todo esto se queda en Databricks. Lo único que se puede pegar al asistente de
código es `resumen_compartible`: errores relativos y en mm, recuentos y alias `E01`, `E02`…, sin
tags, nombres de archivo ni dimensiones (docs/FLUJO_IA.md).
"""

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from statistics import fmean, median

import ifcopenshell
import ifcopenshell.geom
import numpy as np

from trazia.model import Revision

from .referencia import compare_revision, read_reference

MUESTRAS = 4000
ESCALA_MM = 50.0  # tope de color del mapa de calor: igual para todos los equipos


def _clave(texto: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", texto.upper())


def _natural(texto: str) -> list[tuple]:
    """Orden natural que admite mezclar cifras y letras: rev2 < rev10, B < C."""
    return [
        (0, int(t), "") if t.isdigit() else (1, 0, t.upper()) for t in re.split(r"(\d+)", texto)
    ]


def emparejar(tags: list[str], carpeta: Path) -> tuple[dict[str, Path], dict[str, str], int]:
    """{tag: IFC} por nombre: el tag entero (sin separadores) dentro del nombre del archivo.

    `V-1` no casa con `V-10`. Si varios IFC casan, se toma el de revisión más alta según el orden
    natural del nombre y se anota. Devuelve también las notas y cuántos IFC quedaron sin equipo.
    """
    ifcs = sorted(p for p in Path(carpeta).rglob("*") if p.suffix.lower() == ".ifc")
    usados, elegidos, notas = set(), {}, {}
    for tag in tags:
        letras = [re.escape(c) for c in _clave(tag)]
        if not letras:
            continue
        patron = re.compile(r"(?<![A-Z0-9])" + r"[^A-Z0-9]*".join(letras) + r"(?![A-Z0-9])")
        candidatos = [p for p in ifcs if patron.search(p.stem.upper())]
        exactos = [p for p in candidatos if _clave(p.stem) == _clave(tag)]
        candidatos = exactos or candidatos
        if not candidatos:
            continue
        if len(candidatos) > 1:
            notas[tag] = f"{len(candidatos)} IFC casan con el equipo: se usa el último por nombre."
        elegido = max(candidatos, key=lambda p: _natural(p.stem))
        elegidos[tag] = elegido
        usados.update(candidatos)
    return elegidos, notas, len(set(ifcs) - usados)


def superficie(model: ifcopenshell.file) -> tuple[np.ndarray, np.ndarray, int]:
    """Todas las mallas del IFC juntas: vértices en mm, caras y elementos sin geometría legible."""
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    vertices, caras, desplazamiento, fallidos = [], [], 0, 0
    for product in model.by_type("IfcElement"):
        if not product.Representation:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except RuntimeError:
            fallidos += 1
            continue
        v = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3) * 1000
        f = np.array(shape.geometry.faces, dtype=np.int64).reshape(-1, 3)
        if not len(v) or not len(f):
            continue
        vertices.append(v)
        caras.append(f + desplazamiento)
        desplazamiento += len(v)
    if not vertices:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64), fallidos
    return np.vstack(vertices), np.vstack(caras), fallidos


def al_marco(puntos: np.ndarray, lectura: dict, convencion: dict | None = None) -> np.ndarray:
    """Coordenadas del equipo: eje del cuerpo en z, centro en (0, 0) y la cota más baja en 0.

    Con `convencion` ({"sign", "offset"}) se aplica a nuestro modelo el mismo cambio de azimut que
    encontró `compare_revision`, para que sus boquillas caigan sobre las de la referencia.
    """
    marco = lectura["frame"]
    eje = "xyz".index(lectura["axis"])
    a, b = marco["across"]
    local = np.column_stack(
        (
            puntos[:, a] - marco["center"][0],
            puntos[:, b] - marco["center"][1],
            puntos[:, eje] - marco["base"],
        )
    )
    if convencion:
        if convencion["sign"] < 0:
            local[:, 1] *= -1
        giro = math.radians(convencion["offset"])
        c, s = math.cos(giro), math.sin(giro)
        local[:, :2] = local[:, :2] @ np.array([[c, s], [-s, c]])
    return local


def distancias(nuestro, referencia, *, muestras=MUESTRAS, semilla=2026) -> dict:
    """Distancias entre superficies en mm en los dos sentidos, más la de cada vértice nuestro."""
    import trimesh

    from trazia.families.metrics import _distance_to_surface, bbox_iou

    malla_n = trimesh.Trimesh(*nuestro, process=False)
    malla_r = trimesh.Trimesh(*referencia, process=False)

    def puntos(malla):
        muestra, _ = trimesh.sample.sample_surface(malla, muestras, seed=semilla)
        return np.vstack((malla.vertices, muestra))

    sobra = _distance_to_surface(malla_r, puntos(malla_n))  # lo nuestro que no está en TR
    falta = _distance_to_surface(malla_n, puntos(malla_r))  # lo de TR que no hemos modelado
    return {
        "hausdorff_mm": float(max(sobra.max(), falta.max())),
        "p95_mm": float(max(np.percentile(sobra, 95), np.percentile(falta, 95))),
        "chamfer_mm": float((sobra.mean() + falta.mean()) / 2),
        "nuestro_a_referencia_p95_mm": float(np.percentile(sobra, 95)),
        "referencia_a_nuestro_p95_mm": float(np.percentile(falta, 95)),
        "iou_cajas": bbox_iou(malla_n.vertices, malla_r.vertices),
        "muestras": muestras,
        "vertices": _distance_to_surface(malla_r, malla_n.vertices),
    }


def mapa_de_calor(nuestro, referencia, por_vertice, *, escala_mm=ESCALA_MM, titulo=""):
    """Figura de Plotly: nuestro modelo coloreado por distancia (mm) y la referencia en gris."""
    import plotly.graph_objects as go

    def malla(vertices, caras, **extra):
        v, f = vertices / 1000, caras
        return go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2], **extra)

    figura = go.Figure(
        [
            malla(*referencia, color="#9aa5ad", opacity=0.22, name="TR", hoverinfo="skip"),
            malla(
                *nuestro,
                intensity=np.minimum(por_vertice, escala_mm * 4),
                cmin=0,
                cmax=escala_mm,
                colorscale="Turbo",
                colorbar={"title": "mm"},
                name="TrazIA",
                hovertemplate="%{intensity:.0f} mm<extra></extra>",
            ),
        ]
    )
    figura.update_layout(
        title=titulo,
        height=620,
        margin={"l": 0, "r": 0, "b": 0, "t": 40 if titulo else 0},
        scene={"aspectmode": "data", "xaxis_title": "m", "yaxis_title": "m", "zaxis_title": "m"},
        showlegend=False,
    )
    return figura


def disfrazar(model: ifcopenshell.file, *, dx=12.0, dy=-3.5, dz=104.0, grados=90.0):
    """Un IFC nuestro como si viniera de fuera: sin nombres, trasladado (m) y girado en planta.

    Sirve para ensayar la evaluación sin los IFC de TR; el resultado esperado es error ~0 con el
    convenio de azimut `{"sign": 1, "offset": grados}`.
    """
    giro = math.radians(grados)
    padre = model.create_entity(
        "IfcLocalPlacement",
        RelativePlacement=model.create_entity(
            "IfcAxis2Placement3D",
            Location=model.create_entity("IfcCartesianPoint", Coordinates=(dx, dy, dz)),
            Axis=model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
            RefDirection=model.create_entity(
                "IfcDirection", DirectionRatios=(math.cos(giro), math.sin(giro), 0.0)
            ),
        ),
    )
    for product in model.by_type("IfcProduct"):
        placement = product.ObjectPlacement
        if placement and placement.is_a("IfcLocalPlacement") and placement.PlacementRelTo is None:
            placement.PlacementRelTo = padre
    for index, element in enumerate(model.by_type("IfcElement")):
        element.Name = f"Solid {index}"
        element.Tag = None
    return model


def referencias_de_ensayo(lote: Path, destino: Path, *, revision: str = "ultima") -> int:
    """Escribe en `destino` un IFC disfrazado por equipo del lote (`<TAG>_ensayo.ifc`)."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    elegidas = _elegir(_filas(lote), revision)
    for tag, fila in elegidas.items():
        modelo = ifcopenshell.open(str(Path(lote) / tag / f"rev{fila['revision']}" / "modelo.ifc"))
        disfrazar(modelo).write(str(destino / f"{tag}_ensayo.ifc"))
    return len(elegidas)


def _convencion_por_exclusion(tag: str, ajustadas: dict[str, tuple]) -> dict | None:
    otras = Counter(c for t, c in ajustadas.items() if t != tag and c is not None)
    if not otras:
        return None
    (sign, offset), _ = otras.most_common(1)[0]
    return {"sign": sign, "offset": offset}


def _filas(lote: Path) -> list[dict]:
    resumen = Path(lote) / "resumen.json"
    if not resumen.is_file():
        raise FileNotFoundError(f"No hay {resumen}: ejecuta antes el lote (01_procesar_lote)")
    return json.loads(resumen.read_text(encoding="utf-8"))


def _elegir(filas: list[dict], revision: str) -> dict[str, dict]:
    elegidas = {}
    for fila in filas:
        if fila["estado"] != "ok":
            continue
        if revision != "ultima" and fila["revision"].upper() != revision.upper():
            continue
        actual = elegidas.get(fila["tag"])
        if actual is None or _natural(fila["revision"]) > _natural(actual["revision"]):
            elegidas[fila["tag"]] = fila
    return elegidas


def _dimensiones(comparacion: dict) -> dict:
    out = {}
    for nombre, d in comparacion["dimensions"].items():
        relativo = None
        if d["error_mm"] is not None and d["reference"]:
            relativo = d["error_mm"] / d["reference"]
        out[nombre] = {**d, "error_relativo": relativo}
    return out


def _boquillas(comparacion: dict) -> dict | None:
    b = comparacion.get("nozzles")
    if b is None:
        return None
    emparejadas = len(b["matched"])
    return {
        "emparejadas": emparejadas,
        "faltan": b["missing"],
        "sobran": b["extra"],
        "recall": emparejadas / (emparejadas + b["missing"])
        if emparejadas + b["missing"]
        else None,
        "precision": emparejadas / (emparejadas + b["extra"]) if emparejadas + b["extra"] else None,
        "error_posicion_medio_mm": b.get("position_error_mean_mm"),
        "error_posicion_max_mm": b.get("position_error_max_mm"),
        "error_azimut_medio_deg": (
            fmean(m["azimuth_error_deg"] for m in b["matched"]) if b["matched"] else None
        ),
        "sesgo_cota_mm": b.get("elevation_bias_mm"),
        "dn_error_medio_mm": (
            fmean(m["diameter_error_mm"] for m in b["matched"]) if b["matched"] else None
        ),
    }


def evaluar(
    lote: Path,
    referencias: Path,
    *,
    revision: str = "ultima",
    muestras: int = MUESTRAS,
    mapas: Path | None = None,
    escala_mm: float = ESCALA_MM,
) -> dict:
    """Compara la salida de un lote con los IFC de referencia. Ver el docstring del módulo."""
    filas = _filas(lote)
    tags = list(dict.fromkeys(f["tag"] for f in filas))
    alias = {tag: f"E{i:02d}" for i, tag in enumerate(tags, 1)}
    elegidas = _elegir(filas, revision)
    pares, notas_emparejado, ifc_sueltos = emparejar(list(elegidas), referencias)

    leidos = {}
    for tag, ifc in pares.items():
        fila = elegidas[tag]
        carpeta = Path(lote) / tag / f"rev{fila['revision']}"
        rev = Revision.model_validate_json((carpeta / "revision.json").read_text(encoding="utf-8"))
        modelo_ref = ifcopenshell.open(str(ifc))
        modelo_nuestro = ifcopenshell.open(str(carpeta / "modelo.ifc"))
        lectura = read_reference(modelo_ref)
        leidos[tag] = {
            "fila": fila,
            "ifc": ifc,
            "revision": rev,
            "lectura": lectura,
            "lectura_nuestra": read_reference(modelo_nuestro),
            "modelo_ref": modelo_ref,
            "modelo_nuestro": modelo_nuestro,
            "ajustada": compare_revision(rev, lectura) if lectura["diameter"] else None,
        }
    ajustadas = {}
    for tag, d in leidos.items():
        conv = (d["ajustada"] or {}).get("convention")
        ajustadas[tag] = (conv["sign"], conv["offset"]) if conv else None

    equipos = []
    for tag, d in leidos.items():
        lectura, notas = d["lectura"], list(d["lectura"]["notes"])
        if tag in notas_emparejado:
            notas.append(notas_emparejado[tag])
        fila = {
            "tag": tag,
            "alias": alias[tag],
            "revision": d["fila"]["revision"],
            "referencia": d["ifc"].name,
            "familia": d["fila"].get("familia"),
            "notas": notas,
        }
        if d["ajustada"] is None:
            notas.append("La referencia no tiene un cuerpo legible: sin medir.")
            equipos.append(fila)
            continue
        exclusion = _convencion_por_exclusion(tag, ajustadas)
        final = (
            compare_revision(d["revision"], lectura, convention=exclusion) if exclusion else None
        )
        usada = final or d["ajustada"]
        conv_ajustada = d["ajustada"]["convention"]
        fila.update(
            dimensiones=_dimensiones(usada),
            boquillas=_boquillas(usada),
            boquillas_ajustadas=_boquillas(d["ajustada"]),
            convencion={
                "ajustada": conv_ajustada and {k: conv_ajustada[k] for k in ("sign", "offset")},
                "exclusion": exclusion,
                "estable": exclusion is not None
                and (exclusion["sign"], exclusion["offset"]) == ajustadas[tag],
                "cifra": "exclusion_de_uno" if final else "ajustada_en_el_equipo",
            },
        )
        convencion = (final or d["ajustada"])["convention"]
        nuestro = superficie(d["modelo_nuestro"])
        referencia = superficie(d["modelo_ref"])
        if d["lectura_nuestra"].get("frame") and len(nuestro[0]) and len(referencia[0]):
            nuestro = (al_marco(nuestro[0], d["lectura_nuestra"], convencion), nuestro[1])
            referencia = (al_marco(referencia[0], lectura), referencia[1])
            medidas = distancias(nuestro, referencia, muestras=muestras)
            por_vertice = medidas.pop("vertices")
            fila["superficie"] = medidas
            if mapas is not None:
                Path(mapas).mkdir(parents=True, exist_ok=True)
                figura = mapa_de_calor(
                    nuestro,
                    referencia,
                    por_vertice,
                    escala_mm=escala_mm,
                    titulo=f"{tag} rev{fila['revision']} · Chamfer {medidas['chamfer_mm']:.0f} mm",
                )
                destino = Path(mapas) / f"mapa_{re.sub(r'[^A-Za-z0-9_-]+', '-', tag)}.html"
                figura.write_html(destino, include_plotlyjs="cdn")
                fila["mapa"] = str(destino)
        else:
            notas.append("Sin superficie comparable: falta geometría en uno de los dos IFC.")
        equipos.append(fila)

    return {
        "lote": str(lote),
        "revision": revision,
        "equipos": equipos,
        "sin_referencia": [t for t in elegidas if t not in pares],
        "sin_revision_correcta": [t for t in tags if t not in elegidas],
        "ifc_sin_equipo": ifc_sueltos,
        "agregado": agregar(equipos),
    }


def _media(valores):
    valores = [v for v in valores if v is not None]
    return fmean(valores) if valores else None


def _mediana(valores):
    valores = [v for v in valores if v is not None]
    return median(valores) if valores else None


def agregar(equipos: list[dict]) -> dict:
    medidos = [e for e in equipos if "dimensiones" in e]
    boquillas = [e["boquillas"] for e in medidos if e.get("boquillas")]
    emparejadas = sum(b["emparejadas"] for b in boquillas)
    faltan = sum(b["faltan"] for b in boquillas)
    sobran = sum(b["sobran"] for b in boquillas)
    superficies = [e["superficie"] for e in medidos if e.get("superficie")]
    return {
        "equipos_medidos": len(medidos),
        "error_relativo_medio": {
            nombre: _media(e["dimensiones"][nombre]["error_relativo"] for e in medidos)
            for nombre in ("diameter", "height")
        },
        "error_mm_mediano": {
            nombre: _mediana(e["dimensiones"][nombre]["error_mm"] for e in medidos)
            for nombre in ("diameter", "height")
        },
        "boquillas": {
            "emparejadas": emparejadas,
            "faltan": faltan,
            "sobran": sobran,
            "recall": emparejadas / (emparejadas + faltan) if emparejadas + faltan else None,
            "precision": emparejadas / (emparejadas + sobran) if emparejadas + sobran else None,
            "error_posicion_medio_mm": _media(b["error_posicion_medio_mm"] for b in boquillas),
            "error_azimut_medio_deg": _media(b["error_azimut_medio_deg"] for b in boquillas),
        },
        "superficie": {
            "chamfer_mm_medio": _media(s["chamfer_mm"] for s in superficies),
            "p95_mm_medio": _media(s["p95_mm"] for s in superficies),
            "hausdorff_mm_max": max((s["hausdorff_mm"] for s in superficies), default=None),
        },
        "convencion_estable": sum(e["convencion"]["estable"] for e in medidos),
    }


def _redondeo(valor, cifras=3):
    return None if valor is None else round(valor, cifras)


def _redondear(valor):
    if isinstance(valor, dict):
        return {k: _redondear(v) for k, v in valor.items()}
    return round(valor, 4) if isinstance(valor, float) else valor


def resumen_compartible(evaluacion: dict) -> dict:
    """Lo que se puede pegar al asistente: sin tags, archivos, dimensiones ni cotas.

    Las dimensiones van solo como error relativo: con el error en mm y el relativo juntos se
    despejaría la dimensión real. Boquillas y superficie, en mm de error, que no dicen nada del
    equipo por sí solos.
    """
    por_equipo = []
    for e in evaluacion["equipos"]:
        fila = {"equipo": e["alias"], "familia": e.get("familia"), "notas": len(e["notas"])}
        if "dimensiones" in e:
            fila["error_relativo"] = {
                k: _redondeo(v["error_relativo"], 4) for k, v in e["dimensiones"].items()
            }
            b = e.get("boquillas")
            fila["boquillas"] = b and {
                k: _redondeo(v, 3) if isinstance(v, float) else v
                for k, v in b.items()
                if k != "sesgo_cota_mm"
            }
            fila["convencion_estable"] = e["convencion"]["estable"]
            fila["cifra"] = e["convencion"]["cifra"]
            s = e.get("superficie")
            fila["superficie_mm"] = s and {
                k.removesuffix("_mm"): _redondeo(v, 1) for k, v in s.items() if k.endswith("_mm")
            }
        por_equipo.append(fila)
    agregado = _redondear(evaluacion["agregado"])
    agregado.pop("error_mm_mediano", None)
    return {
        "equipos_con_referencia": len(evaluacion["equipos"]),
        "equipos_sin_referencia": len(evaluacion["sin_referencia"]),
        "equipos_sin_revision_correcta": len(evaluacion["sin_revision_correcta"]),
        "ifc_sin_equipo": evaluacion["ifc_sin_equipo"],
        "agregado": agregado,
        "por_equipo": por_equipo,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evalúa un lote contra IFC de referencia")
    parser.add_argument("lote", type=Path, help="Salida de `trazia lote` (con resumen.json)")
    parser.add_argument("referencias", type=Path, help="Carpeta con los IFC de referencia")
    parser.add_argument("--revision", default="ultima", help="Etiqueta o «ultima»")
    parser.add_argument("--muestras", type=int, default=MUESTRAS)
    parser.add_argument("--mapas", type=Path, default=None, help="Carpeta para los mapas HTML")
    parser.add_argument("--escala-mm", type=float, default=ESCALA_MM)
    parser.add_argument("-o", "--output", type=Path, default=None, help="JSON completo")
    parser.add_argument(
        "--compartible", action="store_true", help="Imprimir solo el resumen para el asistente"
    )
    args = parser.parse_args(argv)
    evaluacion = evaluar(
        args.lote,
        args.referencias,
        revision=args.revision,
        muestras=args.muestras,
        mapas=args.mapas,
        escala_mm=args.escala_mm,
    )
    texto = json.dumps(evaluacion, ensure_ascii=False, indent=2, default=str)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(texto, encoding="utf-8")
    salida = resumen_compartible(evaluacion) if args.compartible else evaluacion
    print(json.dumps(salida, ensure_ascii=False, indent=2, default=str))
    return 0 if evaluacion["equipos"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
