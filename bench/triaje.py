"""Triaje de un lote: qué falla, en qué etapa y cuántas veces, sin datos del plano.

    uv run python -m bench.triaje <salida_del_lote> [--json triaje.json]

Lee `resumen.json` y los `eventos.json` de cada revisión que escribe `trazia lote`, agrupa los
fallos por categoría de error y por la primera etapa que falla, y devuelve los cinco problemas
más frecuentes con la plantilla de docs/FLUJO_IA.md ya rellena. Los equipos salen como `E01`,
`E02`… (el mismo alias que `trazia.lote.resumen_compartible`) y nunca se copian textos de error,
avisos ni detalles de eventos: pueden citar valores, tags o nombres de archivo.

El patrón observado («cotas en pulgadas», «hoja girada»…) lo escribe la persona mirando el
documento en Databricks; el triaje solo le dice por dónde empezar.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ORDEN_ETAPAS = (
    "ingest",
    "classify",
    "ocr",
    "extract_tables",
    "extract_labels",
    "extract_hdm",
    "geometry2d",
    "rag",
    "vision",
    "memory",
    "reconcile",
    "calibrate",
    "validate",
    "family",
    "ifc",
)


def _eventos(lote: Path, fila: dict) -> dict:
    carpetas = [lote / fila["tag"] / f"rev{fila['revision']}"]
    if fila.get("carpeta"):
        carpetas.append(Path(fila["carpeta"]))  # ruta absoluta de cuando se lanzó el lote
    for carpeta in carpetas:
        path = carpeta / "eventos.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return {"eventos": [], "avisos": [], "error": fila.get("error")}


def _primera_etapa_con_error(eventos: list[dict]) -> str | None:
    for evento in eventos:
        if evento.get("status") == "error":
            return evento.get("stage") or "desconocida"
    return None


def triar(lote: Path, maximo: int = 5) -> dict:
    """Agregados del fallo por categoría y etapa; se pueden pegar al asistente de código."""
    from trazia.lote import _tipo_error

    lote = Path(lote)
    filas = json.loads((lote / "resumen.json").read_text(encoding="utf-8"))
    alias = {tag: f"E{i:02d}" for i, tag in enumerate(dict.fromkeys(f["tag"] for f in filas), 1)}
    grupos: dict[tuple[str, str], list[str]] = defaultdict(list)
    etapas_error, etapas_omitidas = Counter(), Counter()
    revisiones_con_avisos = 0
    for i, fila in enumerate(filas, 1):
        datos = _eventos(lote, fila)
        eventos = datos.get("eventos") or []
        for evento in eventos:
            if evento.get("status") == "error":
                etapas_error[evento.get("stage") or "desconocida"] += 1
            elif evento.get("status") == "omitido":
                etapas_omitidas[evento.get("stage") or "desconocida"] += 1
        if datos.get("avisos"):
            revisiones_con_avisos += 1
        if fila["estado"] == "ok":
            continue
        categoria = _tipo_error(fila.get("error")) or "sin_categoria"
        etapa = _primera_etapa_con_error(eventos)
        if etapa is None:
            etapa = "ifc" if categoria == "ifc_invalido" else "sin_evento_de_error"
        grupos[(categoria, etapa)].append(f"{alias[fila['tag']]}/{i}")

    problemas = sorted(grupos.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    total = len(filas)
    fallidas = sum(len(v) for v in grupos.values())

    def orden(etapa):
        return ORDEN_ETAPAS.index(etapa) if etapa in ORDEN_ETAPAS else len(ORDEN_ETAPAS)

    return {
        "revisiones": total,
        "equipos": len(alias),
        "fallidas": fallidas,
        "revisiones_con_avisos": revisiones_con_avisos,
        "etapas_con_error": dict(sorted(etapas_error.items(), key=lambda kv: orden(kv[0]))),
        "etapas_omitidas": dict(sorted(etapas_omitidas.items(), key=lambda kv: orden(kv[0]))),
        "problemas": [
            {
                "categoria": categoria,
                "etapa": etapa,
                "revisiones": len(casos),
                "casos": casos[:10],
            }
            for (categoria, etapa), casos in problemas[:maximo]
        ],
        "otros_problemas": max(len(problemas) - maximo, 0),
    }


def peticiones(triaje: dict) -> list[str]:
    """La plantilla de docs/FLUJO_IA.md, una por problema, con el patrón por rellenar."""
    salida = []
    for problema in triaje["problemas"]:
        salida.append(
            f"En la plataforma, {problema['revisiones']} de {triaje['revisiones']} revisiones "
            f"fallan con la categoría {problema['categoria']} en la etapa {problema['etapa']}.\n"
            f"Resumen para el asistente: {json.dumps(problema, ensure_ascii=False)}.\n"
            "Patrón observado (sin datos del plano): <mirar el documento de "
            f"{problema['casos'][0]} en Databricks y describirlo>.\n"
            "Reprodúcelo con un caso sintético, añade una prueba que falle y arréglalo sin "
            "romper el resto."
        )
    return salida


def informe(triaje: dict) -> str:
    lineas = [
        f"{triaje['fallidas']} de {triaje['revisiones']} revisiones fallan "
        f"({triaje['equipos']} equipos, {triaje['revisiones_con_avisos']} revisiones con avisos).",
    ]
    if triaje["etapas_con_error"]:
        etapas = ", ".join(f"{k} {v}" for k, v in triaje["etapas_con_error"].items())
        lineas.append(f"Eventos de error por etapa: {etapas}.")
    if not triaje["problemas"]:
        lineas.append("Sin fallos: nada que triar.")
        return "\n".join(lineas) + "\n"
    lineas += ["", "Problemas, del más frecuente al menos:"]
    for n, problema in enumerate(triaje["problemas"], 1):
        lineas.append(
            f"{n}. {problema['categoria']} en {problema['etapa']}: {problema['revisiones']} "
            f"revisiones ({', '.join(problema['casos'][:5])})"
        )
    if triaje["otros_problemas"]:
        lineas.append(f"… y {triaje['otros_problemas']} combinaciones más con menos casos.")
    lineas += ["", "Peticiones para el asistente (rellenar el patrón antes de pegar):", ""]
    for peticion in peticiones(triaje):
        lineas += ["```text", peticion, "```", ""]
    return "\n".join(lineas)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Triaje de fallos de un lote")
    parser.add_argument("lote", type=Path, help="Carpeta de salida de `trazia lote`")
    parser.add_argument("--json", type=Path, default=None, help="Guardar el triaje en JSON")
    parser.add_argument("--maximo", type=int, default=5)
    args = parser.parse_args(argv)
    resultado = triar(args.lote, args.maximo)
    if args.json:
        args.json.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(informe(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
