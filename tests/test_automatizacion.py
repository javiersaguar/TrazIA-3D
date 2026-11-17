"""Herramientas del evento: guardián, cifras del pitch, sintéticos por perfil y triaje."""

import importlib
import json
import sys
from pathlib import Path

import pytest

from bench import cifras as modulo_cifras
from bench.triaje import informe, peticiones, triar
from synthetic.desde_perfil import generar_parecido, plan
from synthetic.vendors import VENDORS

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def guardian(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    modulo = importlib.import_module("guardian_datos")
    monkeypatch.setattr(modulo, "RAIZ", tmp_path)
    return modulo


def test_guardian_bloquea_datos_claves_y_salidas(guardian, tmp_path):
    clave = "sk-" + "ant-" + "a" * 30  # partida para que el propio guardián no salte aquí
    archivos = {
        "data/private/notas.txt": "x",
        ".env": "X=1",
        ".env.example": "X=",
        "docs/plano.pdf": "%PDF",
        "examples/documents/GAD_V-101_revA.pdf": "%PDF",
        "src/HDM_V-9_rev1.txt": "x",
        "salida/V-101/rev1/revision.json": "{}",
        "src/config.py": f"KEY = '{clave}'",
        "src/limpio.py": "print('hola')",
    }
    for ruta, texto in archivos.items():
        (tmp_path / ruta).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ruta).write_text(texto, encoding="utf-8")
    problemas = guardian.revisar(sorted(archivos), "todo", ["examples/"])
    texto = "\n".join(problemas)
    assert "data/private/notas.txt" in texto
    assert ".env:" in texto and ".env.example" not in texto
    assert "docs/plano.pdf" in texto
    assert "GAD_V-101_revA.pdf" not in texto  # examples/ está permitido
    assert "src/HDM_V-9_rev1.txt: nombre del dataset" in texto
    assert "revision.json: salida del lote" in texto
    assert "src/config.py: parece contener una clave de Anthropic" in texto
    assert clave not in texto  # nunca cita el contenido
    assert "limpio" not in texto


def test_guardian_historial_solo_mira_rutas(guardian, tmp_path):
    assert guardian.revisar(["src/config.py"], "historial", []) == []
    assert guardian.revisar(["docs/a.xlsx"], "historial", [])


def test_permitidos_del_repo_cubren_lo_versionado():
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        modulo = importlib.import_module("guardian_datos")
    finally:
        sys.path.remove(str(RAIZ / "scripts"))
    patrones = modulo.permitidos()
    assert "examples/" in patrones
    assert modulo.esta_permitido("pitch/web/public/logo.png", patrones)
    assert not modulo.esta_permitido("generated/salida/modelo.ifc", patrones)


def _perfil(**cambios) -> dict:
    perfil = {
        "archivos": {"total": 20},
        "equipos": {
            "total": 10,
            "revisiones_por_equipo": {"1": 4, "2": 5, "3": 1},
            "documentos_por_tipo": {"GA": 16, "HDM": 8, "VESOR": 2},
            "combinaciones_de_tipos": {"GA+HDM": 6, "GA": 4},
        },
        "pdf": {
            "documentos": 18,
            "clase": {"vectorial": 10, "escaneado": 8},
            "paginas_por_documento": {"n": 18, "min": 1, "mediana": 1, "max": 6},
            "formato_de_pagina": {"A3": 12, "A1": 6},
            "rotacion_declarada": {"0": 15, "90": 3},
            "con_texto_girado": 2,
        },
        "ifc": {"archivos": 3},
        "imagenes": {"documentos": 0},
        "contenido": {
            "documentos_con_texto": 10,
            "documentos_con_patron": {"unidad_pulgadas": 3, "coma_decimal": 4, "nps": 3},
            "idioma": {"es": 4, "en": 3},
        },
    }
    for clave, valor in cambios.items():
        perfil[clave] = valor
    return perfil


def test_plan_sigue_la_mezcla_del_perfil_y_nunca_usa_reservados():
    p = plan(_perfil())
    assert p["casos"] == 10
    assert not any(VENDORS[v].reserved for v in p["proveedores"])
    imperial = [v for v in p["proveedores"] if VENDORS[v].length_unit != "mm"]
    espanol = [v for v in p["proveedores"] if VENDORS[v].lang == "es"]
    assert len(imperial) == 3 and len(espanol) == 4
    assert p["degradaciones"] == ["vectorial", "escaneado_limpio", "escaneado_pobre"]
    assert p["sin_hoja_de_datos_cada"] == 2  # 4 de 10 equipos sin HDM
    assert p["paquete_cada"] == 4
    huecos = "\n".join(p["huecos"])
    assert "giradas" in huecos and "A1" in huecos and "más de dos revisiones" in huecos
    assert "VESOR" in huecos


def test_plan_sin_texto_usa_todos_los_publicos():
    contenido = {"documentos_con_texto": 0, "documentos_con_patron": {}, "idioma": {}}
    p = plan(_perfil(contenido=contenido), casos=3)
    assert p["casos"] == 3 and len(p["proveedores"]) == 6


def test_generar_parecido_escribe_el_conjunto_y_el_plan(tmp_path):
    resultado = generar_parecido(_perfil(), tmp_path, casos=2)
    raiz = Path(resultado["carpeta"])
    assert json.loads((raiz / "plan.json").read_text(encoding="utf-8"))["casos"] == 2
    manifest = json.loads((raiz / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True and len(manifest["cases"]) == 2


def _lote(tmp_path) -> Path:
    filas = []
    for tag, rev, error, etapa in [
        ("V-101", "A", None, None),
        ("V-101", "B", "IFC inválido: falta la virola de 1200 mm", None),
        ("P-2001A", "1", "ValueError: no se lee 3/4 in", "extract_tables"),
        ("C-300", "1", "ValueError: otra cosa", "extract_tables"),
    ]:
        filas.append(
            {
                "tag": tag,
                "revision": rev,
                "documentos": [f"GAD_{tag}_rev{rev}.pdf"],
                "estado": "error" if error else "ok",
                "error": error,
                "segundos": 1.0,
                "carpeta": "/Volumes/no/existe",
            }
        )
        eventos = [{"stage": "ingest", "status": "ok", "file": "x", "detail": "secreto"}]
        if etapa:
            eventos.append({"stage": etapa, "status": "error", "file": "x", "detail": "3/4 in"})
        eventos.append({"stage": "memory", "status": "omitido", "file": "", "detail": ""})
        carpeta = tmp_path / tag / f"rev{rev}"
        carpeta.mkdir(parents=True)
        (carpeta / "eventos.json").write_text(
            json.dumps({"eventos": eventos, "avisos": ["V-101 aviso"], "error": error}),
            encoding="utf-8",
        )
    (tmp_path / "resumen.json").write_text(json.dumps(filas), encoding="utf-8")
    return tmp_path


def test_triaje_agrupa_por_categoria_y_etapa_sin_datos_del_plano(tmp_path):
    triaje = triar(_lote(tmp_path))
    assert triaje["revisiones"] == 4 and triaje["equipos"] == 3 and triaje["fallidas"] == 3
    assert triaje["etapas_con_error"] == {"extract_tables": 2}
    assert triaje["etapas_omitidas"] == {"memory": 4}
    primero, segundo = triaje["problemas"]
    assert (primero["categoria"], primero["etapa"], primero["revisiones"]) == (
        "ValueError",
        "extract_tables",
        2,
    )
    assert primero["casos"] == ["E02/3", "E03/4"]
    assert (segundo["categoria"], segundo["etapa"]) == ("ifc_invalido", "ifc")
    texto = json.dumps(triaje) + informe(triaje) + "".join(peticiones(triaje))
    for prohibido in ("V-101", "P-2001A", "3/4 in", "1200", "secreto", "GAD_", "Volumes"):
        assert prohibido not in texto
    assert "2 de 4 revisiones fallan con la categoría ValueError" in peticiones(triaje)[0]


def test_triaje_sin_fallos(tmp_path):
    (tmp_path / "resumen.json").write_text(
        json.dumps([{"tag": "V-1", "revision": "1", "estado": "ok", "error": None}]),
        encoding="utf-8",
    )
    assert "Sin fallos" in informe(triar(tmp_path))


def test_cifras_del_evento_al_pitch_y_al_guion(tmp_path):
    filas = [
        {"tag": "V-101", "revision": "A", "documentos": [], "estado": "ok", "segundos": 2.0},
        {"tag": "V-101", "revision": "B", "documentos": [], "estado": "error", "segundos": 4.0},
    ]
    cifras = modulo_cifras.cifras_evento(_perfil(), filas, None)
    assert cifras["datos"]["equipos"] == 10
    assert cifras["datos"]["revisiones"] == 4 + 10 + 3
    assert cifras["lote"] == {
        "equipos": 1,
        "revisiones": 2,
        "correctas": 1,
        "errores": 1,
        "segundos_total": 6.0,
        "segundos_mediana": 4.0,
    }
    assert "V-101" not in json.dumps(cifras)
    (tmp_path / "pitch" / "web" / "src").mkdir(parents=True)
    pitch, guion = modulo_cifras.aplicar(cifras, tmp_path, minutos_revision=12)
    modulo = pitch.read_text(encoding="utf-8")
    assert modulo.startswith("// Generado") and '"correctas": 1' in modulo
    frases = guion.read_text(encoding="utf-8")
    assert "10 equipos y 17 revisiones" in frases
    assert "No tenemos aún la cifra contra los modelos de TR" in frases
    assert "baja a 320" in frases  # 1600 revisiones × 12 min


def test_frases_con_evaluacion_y_sin_tiempo():
    cifras = {
        "fecha": "2026-11-26",
        "dataset": "real",
        "datos": None,
        "evaluacion": {
            "equipos": 5,
            "error_relativo_diametro": 0.012,
            "boquillas_recall": 0.8,
            "error_posicion_mm": 35.0,
            "chamfer_mm": 20.0,
            "convenio_por_exclusion": True,
        },
    }
    frases = modulo_cifras.frases_guion(cifras)
    assert "error medio del 1,2 %" in frases and "8,0 de cada diez" in frases
    assert "convenio ajustado" not in frases
    assert "no se dice la frase del ahorro" in frases


def _repo_con_origen(tmp_path) -> Path:
    import subprocess

    def git(*args, cwd):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    origen, repo = tmp_path / "origen.git", tmp_path / "repo"
    git("init", "--bare", "-b", "main", str(origen), cwd=tmp_path)
    git("init", "-b", "main", str(repo), cwd=tmp_path)
    for clave, valor in (("user.name", "Equipo"), ("user.email", "equipo@example.com")):
        git("config", clave, valor, cwd=repo)
    git("config", "core.hooksPath", "/dev/null", cwd=repo)
    texto = (RAIZ / "PREVIOUS_WORK.md").read_text(encoding="utf-8")
    (repo / "PREVIOUS_WORK.md").write_text(texto, encoding="utf-8", newline="\n")
    git("add", ".", cwd=repo)
    git("commit", "-m", "Base", cwd=repo)
    git("remote", "add", "origin", str(origen), cwd=repo)
    git("push", "-u", "origin", "main", cwd=repo)
    return repo


def _script(monkeypatch, nombre, repo):
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    modulo = importlib.import_module(nombre)
    monkeypatch.setattr(modulo, "RAIZ", repo)
    if hasattr(modulo, "REGISTRO"):
        monkeypatch.setattr(modulo, "REGISTRO", repo / "PREVIOUS_WORK.md")
    return modulo


def test_arranque_cierra_el_registro_y_etiqueta_la_base(monkeypatch, tmp_path, capsys):
    import subprocess

    repo = _repo_con_origen(tmp_path)
    arranque = _script(monkeypatch, "arranque_evento", repo)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    assert arranque.main([]) == 0  # ensayo: no cambia nada
    assert "pendiente" in (repo / "PREVIOUS_WORK.md").read_text(encoding="utf-8")
    assert arranque.main(["--aplicar", "--push"]) == 0
    texto = (repo / "PREVIOUS_WORK.md").read_text(encoding="utf-8")
    assert f"- Commit exacto de la base: `{base}`." in texto
    assert "- Declaración entregada a la organización: pendiente." in texto
    etiquetado = subprocess.run(
        ["git", "rev-list", "-n", "1", "pre-hackathon-baseline"],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert etiquetado == base
    remoto = subprocess.run(
        ["git", "ls-remote", "--tags", "origin"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert "pre-hackathon-baseline" in remoto
    with pytest.raises(SystemExit, match="ya existe"):
        arranque.main(["--aplicar"])

    entrega = _script(monkeypatch, "entrega", repo)
    informe = entrega.Informe()
    entrega.comprobar_git(informe)
    entrega.comprobar_registro(informe)
    salida = capsys.readouterr().out
    assert "✓ Tag en origin" in salida and "✓ main = origin/main" in salida
    assert "Declaración entregada a la organización: pendiente" in salida
    assert informe.fallos == 1  # solo la declaración, que rellena una persona


def test_entrega_detecta_coautores_y_correos_ajenos(monkeypatch, tmp_path, capsys):
    import subprocess

    repo = _repo_con_origen(tmp_path)
    (repo / ".github").mkdir()
    (repo / ".github" / "autores.txt").write_text("equipo@example.com\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    firma = "Co-" + "Authored-By: Alguien <a@b.c>"
    subprocess.run(["git", "commit", "-m", f"Cambio\n\n{firma}"], cwd=repo, check=True)
    entrega = _script(monkeypatch, "entrega", repo)
    informe = entrega.Informe()
    entrega.comprobar_autoria(informe)
    salida = capsys.readouterr().out
    assert "✓ Autores" in salida and "✗ Commits con coautor o firma" in salida
