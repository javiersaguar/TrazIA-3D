"""Cierre de la base previa al empezar el evento (día 25), sin pasos a mano.

    uv run python scripts/arranque_evento.py                         # ensayo: dice lo que haría
    uv run python scripts/arranque_evento.py --aplicar               # registro, commit y tag
    uv run python scripts/arranque_evento.py --aplicar --push        # y además lo sube
    uv run python scripts/arranque_evento.py --gitlab <url> --aplicar --push

Comprueba que el árbol está limpio, en `main` y al día con `origin/main`. Después rellena el
registro de PREVIOUS_WORK.md (fecha y hora de corte, commit exacto y tag), lo confirma con la
identidad Git de quien lo ejecuta y crea el tag anotado `pre-hackathon-baseline` sobre la base,
no sobre el commit del registro. Con `--gitlab` añade el remoto oficial del evento. Solo sube
con `--push`. La línea «Declaración entregada» queda pendiente: la rellena una persona al
entregarla, y `scripts/entrega.py` lo comprueba.
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TAG = "pre-hackathon-baseline"
REGISTRO = RAIZ / "PREVIOUS_WORK.md"


def git(*argumentos: str, comprobar: bool = True) -> str:
    proceso = subprocess.run(
        ["git", *argumentos], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8"
    )
    if comprobar and proceso.returncode != 0:
        raise SystemExit(f"git {' '.join(argumentos)} falló:\n{proceso.stderr.strip()}")
    return proceso.stdout.strip()


def registro_cerrado(texto: str, fecha: str, commit: str) -> str:
    """PREVIOUS_WORK.md con el registro relleno; deja la declaración como esté."""
    cambios = [
        (
            r"^# Trabajo previo al evento · BORRADOR$",
            f"# Trabajo previo al evento · cerrado {fecha}",
        ),
        (r"El tag todavía no se crea\.", f"El tag `{TAG}` marca esa base."),
        (r"^- Fecha/hora de corte: pendiente\.$", f"- Fecha/hora de corte: {fecha}."),
        (r"^- Commit exacto de la base: pendiente\.$", f"- Commit exacto de la base: `{commit}`."),
        (r"^- Tag publicado: pendiente\.$", f"- Tag publicado: `{TAG}` → `{commit[:12]}`."),
    ]
    for patron, nuevo in cambios:
        texto, n = re.subn(patron, nuevo, texto, flags=re.M)
        if n != 1 and patron.startswith("^- "):  # el título y la frase del tag son opcionales
            raise SystemExit(f"PREVIOUS_WORK.md no tiene la línea esperada ({patron}).")
    return texto


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Cerrar la base previa al evento")
    parser.add_argument("--aplicar", action="store_true", help="Hacer commit y tag (si no, ensayo)")
    parser.add_argument("--push", action="store_true", help="Subir main y el tag a los remotos")
    parser.add_argument("--gitlab", default="", help="URL del repositorio de GitLab del evento")
    args = parser.parse_args(argv)
    ensayo = not args.aplicar

    if git("status", "--porcelain"):
        raise SystemExit("Hay cambios sin confirmar: confirma o descarta antes de cerrar la base.")
    if git("branch", "--show-current") != "main":
        raise SystemExit("Cámbiate a main: la base se cierra sobre main.")
    git("fetch", "origin")
    base = git("rev-parse", "HEAD")
    if base != git("rev-parse", "origin/main"):
        raise SystemExit("main no coincide con origin/main: haz git pull (o push) primero.")
    if git("tag", "-l", TAG):
        raise SystemExit(f"El tag {TAG} ya existe: la base ya está cerrada.")
    remotos = git("remote").split()
    if args.gitlab and "gitlab" in remotos and git("remote", "get-url", "gitlab") != args.gitlab:
        raise SystemExit("Ya hay un remoto gitlab con otra URL: revísalo a mano.")

    fecha = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M %Z").strip()
    nuevo = registro_cerrado(REGISTRO.read_text(encoding="utf-8"), fecha, base)
    autor = f"{git('config', 'user.name')} <{git('config', 'user.email')}>"
    print(f"Base: {base} ({git('log', '-1', '--format=%s', base)})")
    print(f"Corte: {fecha} · commit del registro como {autor}")
    print(f"Tag anotado {TAG} sobre {base[:12]}")
    if args.gitlab and "gitlab" not in remotos:
        print(f"Remoto gitlab: {args.gitlab}")
    destinos = ["origin"] + (["gitlab"] if args.gitlab or "gitlab" in remotos else [])
    print(f"Push: {'main y ' + TAG + ' a ' + ', '.join(destinos) if args.push else 'no'}")
    if ensayo:
        print("\nEnsayo: no se ha cambiado nada. Repite con --aplicar para hacerlo.")
        return 0

    REGISTRO.write_bytes(nuevo.encode("utf-8"))
    git("add", "PREVIOUS_WORK.md")
    git("commit", "-m", f"Cierra el registro de trabajo previo con la base {base[:12]}")
    git("tag", "-a", TAG, base, "-m", f"Base previa a IndesIAhack 2026 ({fecha})")
    if args.gitlab and "gitlab" not in remotos:
        git("remote", "add", "gitlab", args.gitlab)
    print(f"Registro confirmado ({git('rev-parse', '--short', 'HEAD')}) y tag {TAG} creado.")
    if args.push:
        for remoto in destinos:
            git("push", remoto, "main")
            git("push", remoto, TAG)
            print(f"Subido a {remoto}.")
    else:
        print("Sin --push: sube main y el tag cuando el equipo lo confirme.")
    print("Falta a mano: entregar la declaración y rellenar su línea en PREVIOUS_WORK.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
