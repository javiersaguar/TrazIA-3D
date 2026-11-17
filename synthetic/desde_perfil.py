"""Conjunto sintético que se parece al dataset del reto, a partir de su perfil agregado.

    uv run python -m synthetic.desde_perfil perfil.json --salida generated/parecido [--casos 12]

`perfil.json` es la salida de `databricks/02_perfil_dataset` (o `trazia perfil`): solo recuentos,
sin nombres ni textos, así que puede salir de Databricks (docs/FLUJO_IA.md). Con él se elige:

- proveedores públicos en la proporción de idioma, pulgadas y coma decimal observada;
- degradaciones según la parte de PDF escaneados;
- equipos sin hoja de datos y paquetes de varias páginas, según los recuentos.

Los proveedores reservados nunca entran: siguen siendo la medida de generalización. Lo que el
generador no sabe reproducir (giros, formatos A1, más de dos revisiones…) sale en `huecos`,
que es la lista de mejoras del generador para el agente.
"""

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from .sets import SETS, SetSpec, generate_set
from .vendors import PUBLIC, VENDORS

SEMILLA = 2611  # fija y anterior a ver el dataset: no se elige por resultado
RANURAS = 10  # resolución de la mezcla de proveedores


def _grupos() -> dict[str, tuple[str, ...]]:
    publicos = [VENDORS[k] for k in PUBLIC]
    return {
        "imperial": tuple(v.key for v in publicos if v.length_unit != "mm"),
        "es": tuple(v.key for v in publicos if v.length_unit == "mm" and v.lang == "es"),
        "en": tuple(v.key for v in publicos if v.length_unit == "mm" and v.lang == "en"),
    }


def plan(perfil: dict, casos: int | None = None) -> dict:
    """Parámetros del conjunto y lo que queda sin reproducir, todo en palabras y recuentos."""
    pdf, equipos = perfil["pdf"], perfil["equipos"]
    contenido = perfil["contenido"]
    con_texto = contenido["documentos_con_texto"] or 0
    patrones = contenido["documentos_con_patron"]
    idioma = contenido["idioma"]
    grupos = _grupos()

    peso = {"imperial": 0.0, "es": 0.0, "en": 0.0}
    if con_texto:
        imperial = max(patrones.get("unidad_pulgadas", 0), patrones.get("fracciones", 0))
        peso["imperial"] = min(imperial / con_texto, 1.0)
        es, en = idioma.get("es", 0), idioma.get("en", 0)
        if patrones.get("coma_decimal", 0) and not es:
            es = patrones["coma_decimal"]  # coma decimal sin palabras: estilo español
        resto = 1.0 - peso["imperial"]
        if es + en:
            peso["es"], peso["en"] = resto * es / (es + en), resto * en / (es + en)
        else:
            peso["es"] = peso["en"] = resto / 2
    if sum(peso.values()) == 0:
        vendedores = PUBLIC
        mezcla = "todos los públicos (sin texto que leer en el perfil)"
    else:
        ranuras = {g: round(p * RANURAS) for g, p in peso.items()}
        if not sum(ranuras.values()):
            ranuras[max(peso, key=peso.get)] = 1
        vendedores = tuple(
            grupos[g][i % len(grupos[g])]
            for g in ("en", "es", "imperial")
            for i in range(ranuras[g])
        )
        mezcla = ", ".join(f"{g} {n}/{sum(ranuras.values())}" for g, n in ranuras.items() if n)

    clase = pdf["clase"]
    escaneados = clase.get("escaneado", 0) + clase.get("mixto", 0)
    vectoriales = clase.get("vectorial", 0) + clase.get("vectorial_sin_texto", 0)
    if escaneados and vectoriales:
        degradaciones = ("vectorial", "escaneado_limpio", "escaneado_pobre")
    elif escaneados:
        degradaciones = ("escaneado_limpio", "escaneado_pobre")
    else:
        degradaciones = ("vectorial",)

    combinaciones = equipos["combinaciones_de_tipos"]
    total = equipos["total"] or 1
    con_hdm = sum(n for k, n in combinaciones.items() if "HDM" in k.split("+"))
    sin_hdm = 1 - con_hdm / total
    no_hdm_every = 0 if sin_hdm < 0.05 else max(1, round(1 / sin_hdm))
    paginas = pdf.get("paginas_por_documento") or {}
    package_every = 4 if (paginas.get("max") or 1) > 2 else 0

    huecos = []
    if pdf["con_texto_girado"] or any(int(r) for r in pdf["rotacion_declarada"]):
        huecos.append("Páginas giradas o con texto girado: el generador no gira páginas.")
    formatos = {f for f in pdf["formato_de_pagina"] if f != "A3"}
    if formatos:
        huecos.append(
            f"Formatos de página {', '.join(sorted(formatos))}: el generador solo dibuja A3."
        )
    if clase.get("vectorial_sin_texto"):
        huecos.append("PDF con el texto en curvas: no hay degradación que lo imite.")
    if any(int(k) > 2 for k in equipos["revisiones_por_equipo"]):
        huecos.append("Equipos con más de dos revisiones: el generador hace rev 1 y rev 2.")
    otros = {k for k in equipos["documentos_por_tipo"] if k not in ("GA", "GAD", "HDM")}
    if otros:
        huecos.append(f"Documentos {', '.join(sorted(otros))}: el generador no los produce.")
    if perfil["imagenes"]["documentos"]:
        huecos.append("Planos como imagen suelta (PNG/JPG/TIFF): el generador entrega PDF.")
    if patrones.get("nps") and not peso["imperial"]:
        huecos.append("NPS con cotas en mm: ningún proveedor público combina las dos cosas.")

    n = casos or min(max(equipos["total"], 4), 24)
    return {
        "casos": n,
        "semilla": SEMILLA,
        "proveedores": list(vendedores),
        "mezcla": mezcla,
        "degradaciones": list(degradaciones),
        "sin_hoja_de_datos_cada": no_hdm_every,
        "paquete_cada": package_every,
        "huecos": huecos,
    }


def generar_parecido(perfil: dict, salida: Path, casos: int | None = None) -> dict:
    p = plan(perfil, casos)
    spec = replace(
        SETS["s-dev"],
        name="s-perfil",
        seed=p["semilla"],
        cases=p["casos"],
        vendors=tuple(p["proveedores"]),
        degradations=tuple(p["degradaciones"]),
        no_hdm_every=p["sin_hoja_de_datos_cada"],
        package_every=p["paquete_cada"],
        tag_offset=300,
    )
    assert isinstance(spec, SetSpec) and not any(VENDORS[v].reserved for v in spec.vendors)
    manifest = generate_set("s-perfil", Path(salida), spec=spec)
    raiz = Path(salida) / "s-perfil"
    (raiz / "plan.json").write_text(
        json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"plan": p, "manifest": manifest, "carpeta": str(raiz)}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Sintéticos parecidos al dataset del perfil")
    parser.add_argument("perfil", type=Path, help="perfil.json de 02_perfil_dataset")
    parser.add_argument("--salida", type=Path, default=Path("generated/parecido"))
    parser.add_argument("--casos", type=int, default=None)
    parser.add_argument("--solo-plan", action="store_true", help="No generar, solo el plan")
    args = parser.parse_args(argv)
    perfil = json.loads(args.perfil.read_text(encoding="utf-8"))
    if args.solo_plan:
        print(json.dumps(plan(perfil, args.casos), ensure_ascii=False, indent=2))
        return 0
    resultado = generar_parecido(perfil, args.salida, args.casos)
    print(json.dumps(resultado["plan"], ensure_ascii=False, indent=2))
    print(f"{len(resultado['manifest']['cases'])} equipos en {resultado['carpeta']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
