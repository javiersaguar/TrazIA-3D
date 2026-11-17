"""Guardián de datos: impide que un documento del reto, una salida real o una clave entre en Git.

    python scripts/guardian_datos.py            # lo que va en el commit (hook pre-commit)
    python scripts/guardian_datos.py --todo     # todos los archivos versionados
    python scripts/guardian_datos.py --historial  # todo lo que ha pasado por la historia

Solo usa la biblioteca estándar: el hook corre sin entorno virtual. Bloquea:

- cualquier cosa en `data/private/` y archivos `.env` (salvo `.env.example`);
- documentos y modelos (PDF, XLSX, IFC, imágenes, CAD, ZIP…) fuera de las carpetas permitidas
  en `.guardian-permitidos`, que son nuestras capturas, ejemplos sintéticos y material de demo;
- nombres del dataset (`GAD_`, `HDM_`, `VESOR_`, `ESTRUCTURA_`) fuera de esas carpetas;
- archivos de más de 5 MB fuera de esas carpetas;
- claves con forma conocida (OpenAI, Groq, Google, NVIDIA, Hugging Face, Databricks, GitLab,
  GitHub, claves privadas) en el contenido de los archivos de texto;
- salidas del lote (`revision.json`, `modelo.ifc`, `eventos.json`, `resumen.json`, `perfil.json`,
  `evaluacion_tr.json`) fuera de las carpetas permitidas.

Si un archivo es legítimo, se añade su carpeta o patrón a `.guardian-permitidos` en un commit
propio que revise otra persona. Nunca se salta con `--no-verify`.
"""

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PERMITIDOS = RAIZ / ".guardian-permitidos"
MAX_BYTES = 5 * 1024 * 1024
DOCUMENTOS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".xlsm",
    ".csv",
    ".ifc",
    ".ifczip",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
    ".dwg",
    ".dxf",
    ".zip",
    ".7z",
    ".rar",
    ".docx",
    ".doc",
    ".pptx",
    ".msg",
    ".eml",
    ".mp4",
    ".mov",
    ".glb",
    ".gltf",
}
NOMBRE_DATASET = re.compile(r"^(?:GAD|GA|HDM|VESOR|ESTRUCTURA)_.+", re.I)
SALIDAS_LOTE = {
    "revision.json",
    "modelo.ifc",
    "eventos.json",
    "resumen.json",
    "resumen.csv",
    "perfil.json",
    "evaluacion_tr.json",
    "evaluacion_ensayo.json",
    "registro_envios.jsonl",
}
CLAVES = {
    "OpenAI": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "Anthropic": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "Groq": re.compile(r"\bgsk_[A-Za-z0-9]{20,}"),
    "Google": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "NVIDIA": re.compile(r"\bnvapi-[A-Za-z0-9_-]{20,}"),
    "Hugging Face": re.compile(r"\bhf_[A-Za-z0-9]{30,}"),
    "Databricks": re.compile(r"\bdapi[0-9a-f]{32}\b"),
    "GitLab": re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"),
    "GitHub": re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{30,}"),
    "OpenRouter": re.compile(r"\bsk-or-v1-[0-9a-f]{40,}"),
    "Clave privada": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


def permitidos() -> list[str]:
    if not PERMITIDOS.is_file():
        return []
    lineas = PERMITIDOS.read_text(encoding="utf-8").splitlines()
    return [x.strip() for x in lineas if x.strip() and not x.lstrip().startswith("#")]


def esta_permitido(ruta: str, patrones: list[str]) -> bool:
    for patron in patrones:
        if patron.endswith("/") and ruta.startswith(patron):
            return True
        if fnmatch.fnmatch(ruta, patron):
            return True
    return False


def _git(*argumentos: str, entrada: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *argumentos], cwd=RAIZ, input=entrada, capture_output=True, check=True
    ).stdout


def archivos(modo: str) -> list[str]:
    if modo == "staged":
        salida = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    elif modo == "todo":
        salida = _git("ls-files", "-z")
    else:  # historial: cualquier ruta que haya existido en cualquier commit
        salida = _git("log", "--all", "--pretty=format:", "--name-only", "-z", "--diff-filter=AMR")
    rutas = {r for r in salida.decode("utf-8", "replace").split("\0") if r.strip()}
    return sorted(r.strip() for r in rutas)


def contenido(ruta: str, modo: str) -> bytes | None:
    """Lo que va al commit (índice) o lo que hay en disco; None si no existe."""
    try:
        if modo == "staged":
            return _git("show", f":{ruta}")
        path = RAIZ / ruta
        return path.read_bytes() if path.is_file() else None
    except subprocess.CalledProcessError:
        return None


def revisar(rutas: list[str], modo: str = "todo", patrones: list[str] | None = None) -> list[str]:
    """Problemas encontrados, uno por línea, sin citar el contenido de ningún archivo."""
    patrones = permitidos() if patrones is None else patrones
    problemas = []
    for ruta in rutas:
        nombre = ruta.rsplit("/", 1)[-1]
        sufijo = Path(nombre).suffix.lower()
        permitido = esta_permitido(ruta, patrones)
        if ruta.startswith("data/private/"):
            problemas.append(f"{ruta}: data/private/ nunca se versiona")
            continue
        if (nombre == ".env" or nombre.startswith(".env.")) and nombre != ".env.example":
            problemas.append(f"{ruta}: archivo de entorno con posibles claves")
            continue
        if not permitido:
            if sufijo in DOCUMENTOS:
                problemas.append(
                    f"{ruta}: documento o modelo ({sufijo}) fuera de las carpetas permitidas"
                )
            if NOMBRE_DATASET.match(nombre):
                problemas.append(f"{ruta}: nombre del dataset del reto fuera de examples/")
            if nombre in SALIDAS_LOTE:
                problemas.append(f"{ruta}: salida del lote; se queda en el volumen de Databricks")
        if modo == "historial":
            continue  # en la historia solo se miran rutas: leer cada versión sería muy lento
        datos = contenido(ruta, modo)
        if datos is None:
            continue
        if len(datos) > MAX_BYTES and not permitido:
            problemas.append(f"{ruta}: {len(datos) / 1e6:.1f} MB, más de 5 MB")
        if b"\0" in datos[:8000]:
            continue  # binario: las claves se buscan en texto
        texto = datos.decode("utf-8", "replace")
        for proveedor, patron in CLAVES.items():
            if patron.search(texto):
                problemas.append(f"{ruta}: parece contener una clave de {proveedor}")
    return problemas


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Guardián de datos del repositorio")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--todo", action="store_true", help="Todos los archivos versionados")
    grupo.add_argument("--historial", action="store_true", help="Rutas de toda la historia")
    args = parser.parse_args(argv)
    modo = "todo" if args.todo else "historial" if args.historial else "staged"
    rutas = archivos(modo)
    problemas = revisar(rutas, modo)
    if problemas:
        print("Guardián de datos: commit bloqueado." if modo == "staged" else "Guardián de datos:")
        for problema in problemas:
            print(f"  - {problema}")
        print(
            "Saca esos archivos del commit (git restore --staged <ruta>). Si son legítimos, "
            "añade su carpeta a .guardian-permitidos en un commit aparte."
        )
        return 1
    if modo != "staged":
        print(f"Guardián de datos: {len(rutas)} rutas revisadas, sin problemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
