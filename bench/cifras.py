"""Cifras del evento para el pitch y el guion, sin copiarlas a mano.

En Databricks (notebook `04_todo` o a mano):

    from bench.cifras import cifras_evento
    cifras = cifras_evento(perfil, filas, evaluacion)       # solo agregados, sin tags ni rutas

En el portátil, con el `cifras_evento.json` que sale del notebook:

    uv run python -m bench.cifras aplicar cifras_evento.json [--minutos-revision 12]

escribe `pitch/web/src/cifras-evento.js` (lo lee `pitch-data.js`) y `generated/cifras_guion.md`
con las frases de las marcas [CIFRA TR] de docs/GUION_DEMO.md ya rellenas. Lo que no está
medido sale como «sin medir» y la frase alternativa del guion, nunca como un número.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
HORAS_PROYECTO = 4800  # 400 equipos × 4 revisiones × 3 h (enunciado, pág. 5)
REVISIONES_PROYECTO = 1600


def _fila(fila) -> dict:
    return fila if isinstance(fila, dict) else fila.__dict__


def cifras_evento(perfil=None, filas=None, evaluacion=None, *, dataset="real") -> dict:
    """Agregados que se pueden llevar al portátil y al repositorio (docs/FLUJO_IA.md)."""
    salida = {
        "version": 1,
        "fecha": date.today().isoformat(),
        "dataset": dataset,
        "datos": None,
        "lote": None,
        "evaluacion": None,
    }
    if perfil:
        clase = perfil["pdf"]["clase"]
        pdf = perfil["pdf"]["documentos"]
        escaneados = clase.get("escaneado", 0) + clase.get("mixto", 0)
        salida["datos"] = {
            "equipos": perfil["equipos"]["total"],
            "revisiones": sum(
                int(k) * v for k, v in perfil["equipos"]["revisiones_por_equipo"].items()
            ),
            "pdf": pdf,
            "escaneados": round(escaneados / pdf, 3) if pdf else None,
            "ifc_referencia": perfil["ifc"]["archivos"],
        }
    if filas:
        from trazia.lote import Fila, resumen_compartible

        lote = resumen_compartible([Fila(**_fila(f)) for f in filas])
        salida["lote"] = {
            "equipos": lote["equipos"],
            "revisiones": lote["revisiones"],
            "correctas": lote["estado"].get("ok", 0),
            "errores": lote["estado"].get("error", 0),
            "segundos_total": lote["segundos"]["total"],
            "segundos_mediana": lote["segundos"]["mediana"],
        }
    if evaluacion and evaluacion.get("equipos"):
        from .evaluar import resumen_compartible

        agregado = resumen_compartible(evaluacion)["agregado"]
        boquillas, superficie = agregado["boquillas"], agregado["superficie"]
        exclusion = [e for e in evaluacion["equipos"] if e.get("convencion")]
        salida["evaluacion"] = {
            "equipos": agregado["equipos_medidos"],
            "error_relativo_diametro": agregado["error_relativo_medio"]["diameter"],
            "error_relativo_virola": agregado["error_relativo_medio"]["height"],
            "boquillas_recall": boquillas["recall"],
            "boquillas_precision": boquillas["precision"],
            "error_posicion_mm": boquillas["error_posicion_medio_mm"],
            "error_azimut_deg": boquillas["error_azimut_medio_deg"],
            "chamfer_mm": superficie["chamfer_mm_medio"],
            "p95_mm": superficie["p95_mm_medio"],
            "convenio_por_exclusion": all(
                e["convencion"]["cifra"] == "exclusion_de_uno" for e in exclusion
            )
            and bool(exclusion),
        }
    return salida


def _pct(valor, decimales=1):
    return "sin medir" if valor is None else f"{valor * 100:.{decimales}f}".replace(".", ",")


def _num(valor, decimales=0):
    if valor is None:
        return "sin medir"
    texto = f"{valor:,.{decimales}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return texto


def frases_guion(cifras: dict, minutos_revision: float | None = None) -> str:
    """Las frases con [CIFRA TR] de docs/GUION_DEMO.md, rellenas o con su alternativa."""
    datos, evaluacion = cifras.get("datos"), cifras.get("evaluacion")
    lineas = [
        f"# Cifras para el guion ({cifras['fecha']}, dataset {cifras['dataset']})",
        "",
        "Generado por `python -m bench.cifras aplicar`. No editar a mano: volver a generarlo.",
        "",
        "## 1:00–1:40 · Entran los documentos",
        "",
    ]
    if datos:
        lineas.append(
            f"«Con el dataset del reto hemos hecho lo mismo dentro de la plataforma, en lote: "
            f"{_num(datos['equipos'])} equipos y {_num(datos['revisiones'])} revisiones.»"
        )
    else:
        lineas.append("Sin perfil del dataset: se omite la frase de Databricks.")
    lineas += ["", "## 4:50–5:30 · Medido contra los IFC de TR", ""]
    if evaluacion and evaluacion["equipos"]:
        recall = evaluacion["boquillas_recall"]
        de_diez = "sin medir" if recall is None else _num(recall * 10, 1)
        lineas.append(
            f"«En {_num(evaluacion['equipos'])} equipos, el diámetro tiene un error medio del "
            f"{_pct(evaluacion['error_relativo_diametro'])} % y encontramos {de_diez} de cada "
            "diez boquillas.»"
        )
        if not evaluacion["convenio_por_exclusion"]:
            lineas.append(
                "Aviso: la cifra usa el convenio ajustado en cada equipo (solo hay uno con "
                "referencia). Decirlo así o no citar el error de boquillas."
            )
        lineas.append(
            f"Rótulo: error de diámetro {_pct(evaluacion['error_relativo_diametro'])} % · "
            f"boquillas encontradas {_pct(recall, 0)} % · error de posición "
            f"{_num(evaluacion['error_posicion_mm'])} mm · Chamfer "
            f"{_num(evaluacion['chamfer_mm'])} mm · {evaluacion['equipos']} equipos"
        )
    else:
        lineas.append(
            "«No tenemos aún la cifra contra los modelos de TR; esto es lo que medimos con datos "
            "sintéticos y así lo mediremos con los vuestros.» (bloque de 20 s)"
        )
    lineas += ["", "## Impacto", ""]
    if minutos_revision:
        horas = REVISIONES_PROYECTO * minutos_revision / 60
        lineas.append(
            f"«En revisión asistida tardamos {_num(minutos_revision, 1)} minutos por equipo. Con "
            f"eso, el proyecto de 4.800 horas baja a {_num(horas)}.»"
        )
    else:
        lineas.append("Tiempo de revisión sin medir: no se dice la frase del ahorro.")
    return "\n".join(lineas) + "\n"


def aplicar(cifras: dict, raiz: Path = RAIZ, minutos_revision: float | None = None) -> list[Path]:
    """Escribe el módulo del pitch y la hoja de frases del guion."""
    pitch = raiz / "pitch" / "web" / "src" / "cifras-evento.js"
    guion = raiz / "generated" / "cifras_guion.md"
    contenido = dict(cifras, minutos_revision=minutos_revision)
    pitch.write_text(
        "// Generado por `python -m bench.cifras aplicar`: no editar a mano.\n"
        "// Solo agregados del evento (docs/FLUJO_IA.md). null = sin cifras del evento.\n"
        f"export const cifrasEvento = {json.dumps(contenido, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
        newline="\n",
    )
    guion.parent.mkdir(parents=True, exist_ok=True)
    guion.write_text(frases_guion(cifras, minutos_revision), encoding="utf-8", newline="\n")
    return [pitch, guion]


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Cifras del evento para el pitch y el guion")
    sub = parser.add_subparsers(dest="orden", required=True)
    aplicar_ = sub.add_parser("aplicar", help="Escribir pitch y frases desde cifras_evento.json")
    aplicar_.add_argument("cifras", type=Path)
    aplicar_.add_argument("--minutos-revision", type=float, default=None)
    sub.add_parser("vaciar", help="Volver al pitch solo con cifras sintéticas")
    args = parser.parse_args(argv)
    if args.orden == "vaciar":
        destino = RAIZ / "pitch" / "web" / "src" / "cifras-evento.js"
        destino.write_text(
            "// Generado por `python -m bench.cifras aplicar`: no editar a mano.\n"
            "// Solo agregados del evento (docs/FLUJO_IA.md). null = sin cifras del evento.\n"
            "export const cifrasEvento = null;\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Sin cifras del evento en {destino}")
        return 0
    cifras = json.loads(args.cifras.read_text(encoding="utf-8"))
    for path in aplicar(cifras, minutos_revision=args.minutos_revision):
        print(f"Escrito {path}")
    print(frases_guion(cifras, args.minutos_revision))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
