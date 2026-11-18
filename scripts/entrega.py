"""Comprobación de la entrega del viernes (27/11, 10:00) antes de congelar `main`.

    uv run python scripts/entrega.py              # todo, con el build del pitch
    uv run python scripts/entrega.py --rapido     # sin compilar el pitch

Cada línea es ✓ (bien), ! (aviso: revisar, no bloquea) o ✗ (fallo: no entregar así):

- árbol limpio, en `main` y al día con `origin/main` y, si existe, `gitlab/main`;
- tag `pre-hackathon-baseline` en local y en los remotos;
- PREVIOUS_WORK.md sin «pendiente»;
- guardián de datos sobre lo versionado y sobre toda la historia;
- autores y committers desde el tag en `.github/autores.txt`, y ningún coautor ni firma de
  asistente en los mensajes;
- el pitch compila y tiene las cifras del evento (`pitch/web/src/cifras-evento.js`);
- capturas del guion en docs/capturas/producto/.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TAG = "pre-hackathon-baseline"
FIRMAS = re.compile(r"co-authored-by|generated with|🤖", re.I)


def git(*argumentos: str) -> tuple[int, str]:
    proceso = subprocess.run(
        ["git", *argumentos], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8"
    )
    return proceso.returncode, proceso.stdout.strip()


class Informe:
    def __init__(self):
        self.fallos = self.avisos = 0

    def ok(self, texto):
        print(f"✓ {texto}")

    def aviso(self, texto):
        self.avisos += 1
        print(f"! {texto}")

    def fallo(self, texto):
        self.fallos += 1
        print(f"✗ {texto}")

    def si(self, condicion, bien, mal, *, grave=True):
        if condicion:
            self.ok(bien)
        elif grave:
            self.fallo(mal)
        else:
            self.aviso(mal)


def autores_permitidos() -> set[str]:
    path = RAIZ / ".github" / "autores.txt"
    lineas = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    return {x.strip().lower() for x in lineas if x.strip() and not x.startswith("#")}


def comprobar_git(informe: Informe) -> None:
    _, estado = git("status", "--porcelain")
    informe.si(not estado, "Árbol limpio", "Hay cambios sin confirmar")
    _, rama = git("branch", "--show-current")
    informe.si(rama == "main", "En main", f"Estás en «{rama}», no en main")
    _, remotos = git("remote")
    _, cabeza = git("rev-parse", "HEAD")
    for remoto in [r for r in ("origin", "gitlab") if r in remotos.split()]:
        if git("fetch", "--tags", remoto)[0] != 0:
            informe.aviso(f"No se pudo leer {remoto} (¿sin red?)")
            continue
        _, remota = git("rev-parse", f"{remoto}/main")
        informe.si(cabeza == remota, f"main = {remoto}/main", f"main no coincide con {remoto}/main")
        codigo, tags = git("ls-remote", "--tags", remoto, TAG)
        informe.si(codigo == 0 and TAG in tags, f"Tag en {remoto}", f"Falta el tag en {remoto}")
    if "gitlab" not in remotos.split():
        informe.aviso("No hay remoto gitlab: la entrega oficial va a GitLab")
    informe.si(bool(git("tag", "-l", TAG)[1]), f"Tag {TAG} en local", f"Falta el tag {TAG}")


def comprobar_registro(informe: Informe) -> None:
    texto = (RAIZ / "PREVIOUS_WORK.md").read_text(encoding="utf-8")
    pendientes = [  # líneas del registro («- Tag publicado: pendiente.»), no títulos
        linea.strip() for linea in texto.splitlines() if re.match(r"^- .*: pendiente\.?\s*$", linea)
    ]
    informe.si(
        not pendientes,
        "PREVIOUS_WORK.md cerrado",
        "PREVIOUS_WORK.md tiene pendientes: " + " | ".join(pendientes[:4]),
    )


def comprobar_guardian(informe: Informe) -> None:
    for modo in ("--todo", "--historial"):
        proceso = subprocess.run(
            [sys.executable, "scripts/guardian_datos.py", modo],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        informe.si(
            proceso.returncode == 0,
            f"Guardián {modo}",
            f"Guardián {modo}:\n{proceso.stdout.strip()}",
        )


def comprobar_autoria(informe: Informe) -> None:
    rango = f"{TAG}..HEAD" if git("tag", "-l", TAG)[1] else "HEAD"
    _, salida = git("log", rango, "--format=%H%x1f%ae%x1f%ce%x1f%B%x1e")
    permitidos = autores_permitidos()
    extranos, firmados = set(), []
    for bloque in filter(str.strip, salida.split("\x1e")):
        sha, autor, committer, mensaje = bloque.strip().split("\x1f", 3)
        extranos |= {c for c in (autor.lower(), committer.lower()) if c not in permitidos}
        if FIRMAS.search(mensaje):
            firmados.append(sha[:10])
    informe.si(
        not extranos,
        f"Autores en .github/autores.txt ({rango})",
        f"Correos fuera de .github/autores.txt: {', '.join(sorted(extranos))}",
    )
    informe.si(
        not firmados,
        "Sin coautores ni firmas en los mensajes",
        f"Commits con coautor o firma: {', '.join(firmados[:8])}",
    )
    autores = (RAIZ / ".github" / "autores.txt").read_text(encoding="utf-8").lower()
    if "pendiente" in autores:
        informe.aviso(".github/autores.txt aún tiene correos pendientes del equipo")


def comprobar_pitch(informe: Informe, compilar: bool) -> None:
    cifras = (RAIZ / "pitch" / "web" / "src" / "cifras-evento.js").read_text(encoding="utf-8")
    informe.si(
        "cifrasEvento = null" not in cifras,
        "El pitch tiene las cifras del evento",
        "El pitch solo tiene cifras sintéticas: python -m bench.cifras aplicar cifras_evento.json",
        grave=False,
    )
    if compilar:
        corepack = shutil.which("corepack") or "corepack"  # en Windows es corepack.cmd
        proceso = subprocess.run(
            [corepack, "pnpm@10.18.0", "build"],
            cwd=RAIZ / "pitch" / "web",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        informe.si(
            proceso.returncode == 0,
            "El pitch compila",
            "El pitch no compila:\n" + (proceso.stdout + proceso.stderr)[-1500:],
        )
    capturas = RAIZ / "docs" / "capturas" / "producto"
    hechas = sorted(p.name for p in capturas.glob("demo-0*.png")) if capturas.is_dir() else []
    informe.si(
        len(hechas) >= 6,
        f"{len(hechas)} capturas del guion",
        f"Solo {len(hechas)} capturas del guion: cd web; corepack pnpm capturas:guion",
        grave=False,
    )


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Comprobar la entrega")
    parser.add_argument("--rapido", action="store_true", help="Sin compilar el pitch")
    args = parser.parse_args(argv)
    informe = Informe()
    comprobar_git(informe)
    comprobar_registro(informe)
    comprobar_guardian(informe)
    comprobar_autoria(informe)
    comprobar_pitch(informe, not args.rapido)
    print()
    if informe.fallos:
        print(f"No entregar todavía: {informe.fallos} fallos y {informe.avisos} avisos.")
        return 1
    print(f"Lista para entregar ({informe.avisos} avisos que revisar).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
