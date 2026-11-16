"""Lote por carpeta (Databricks): agrupación por tag y revisión, salidas y resumen."""

import csv
import json
import shutil
from pathlib import Path

import pytest

from trazia import lote
from trazia.cli import main

EJEMPLOS = Path(__file__).resolve().parents[1] / "examples" / "documents"


@pytest.fixture(autouse=True)
def _caches_limpias(monkeypatch):
    """El lote fija variables TRAZIA_*: se restauran al acabar cada prueba."""
    for variable in (*lote.CACHES, "TRAZIA_REGISTRO_ENVIOS"):
        monkeypatch.delenv(variable, raising=False)


def _volumen(tmp_path):
    """Imita `/Volumes/<catálogo>/<esquema>/<volumen>/...` con subcarpetas y ruido."""
    entrada = tmp_path / "Volumes" / "indesia" / "ga2model" / "datos" / "lote1"
    (entrada / "planos").mkdir(parents=True)
    (entrada / "listas").mkdir()
    for path in EJEMPLOS.glob("GAD_*.pdf"):
        shutil.copy(path, entrada / "planos" / path.name)
    for path in EJEMPLOS.glob("HDM_*.xlsx"):
        shutil.copy(path, entrada / "listas" / path.name)
    (entrada / "LEEME.txt").write_text("no es un documento del reto", encoding="utf-8")
    (entrada / "planos" / "otro_V-101.pdf").write_bytes(b"%PDF-1.4")
    return entrada


def test_agrupa_por_tag_y_revision_en_orden(tmp_path):
    for nombre in (
        "GAD_P-7_rev10.pdf",
        "GAD_P-7_rev2.pdf",
        "HDM_P-7_rev2.xlsx",
        "VESOR_P-7.pdf",
        "GAD_T 1_revA.pdf",
        "notas.pdf",
    ):
        (tmp_path / nombre).write_bytes(b"x")
    grupos = lote.agrupar(tmp_path)
    assert list(grupos) == ["P-7", "T 1"]
    assert list(grupos["P-7"]) == ["2", "10"]
    assert [d.path.name for d in grupos["P-7"]["2"]] == [
        "GAD_P-7_rev2.pdf",
        "HDM_P-7_rev2.xlsx",
        "VESOR_P-7.pdf",
    ]
    assert [d.document_id for d in grupos["P-7"]["10"]] == ["GA-P-7", "VESOR-P-7"]
    assert grupos["T 1"]["A"][0].document_id == "GA-T-1"


def test_configurar_cache_respeta_variables_fijadas(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_OCR_CACHE", "/ya/fijada")
    fijadas = lote.configurar_cache(tmp_path)
    assert fijadas["TRAZIA_OCR_CACHE"] == "/ya/fijada"
    assert fijadas["TRAZIA_VISION_CACHE"] == str(tmp_path / "cache" / "vision")
    assert fijadas["TRAZIA_REGISTRO_ENVIOS"] == str(tmp_path / "registro_envios.jsonl")


def test_lote_completo_por_cli(tmp_path):
    entrada, salida = _volumen(tmp_path), tmp_path / "salida"
    codigo = main(
        [
            "lote",
            str(entrada),
            "-o",
            str(salida),
            "--estrategia",
            "b_reglas",
            "--dataset",
            "synthetic",
        ]
    )
    assert codigo == 0
    for etiqueta in ("A", "B"):
        carpeta = salida / "V-101" / f"rev{etiqueta}"
        revision = json.loads((carpeta / "revision.json").read_text(encoding="utf-8"))
        assert revision["revision"] == etiqueta
        assert revision["equipment"]["id"] == "v-101"
        assert revision["run"]["strategy"] == "b_reglas"
        assert (carpeta / "modelo.ifc").read_text(encoding="utf-8").startswith("ISO-10303-21")
        eventos = json.loads((carpeta / "eventos.json").read_text(encoding="utf-8"))
        assert eventos["error"] is None and eventos["eventos"]
    cambios = json.loads((salida / "V-101" / "cambios_revA_revB.json").read_text("utf-8"))
    assert cambios["changes"]
    with (salida / "resumen.csv").open(encoding="utf-8") as handle:
        filas = list(csv.DictReader(handle))
    assert [(f["tag"], f["revision"], f["estado"]) for f in filas] == [
        ("V-101", "A", "ok"),
        ("V-101", "B", "ok"),
    ]
    assert filas[1]["cambios"] == str(len(cambios["changes"]))
    # Las cachés quedan junto a la salida, no en generated/ del repo.
    assert (salida / "_trabajo").is_dir()


def test_un_equipo_roto_no_detiene_el_lote(tmp_path):
    (tmp_path / "entrada").mkdir()
    (tmp_path / "entrada" / "GAD_X-1_rev1.pdf").write_bytes(b"no es un pdf")
    filas = lote.procesar_carpeta(
        tmp_path / "entrada", tmp_path / "salida", estrategia="b_reglas", dataset="synthetic"
    )
    assert len(filas) == 1 and filas[0].estado == "error" and filas[0].error
    resumen = json.loads((tmp_path / "salida" / "resumen.json").read_text(encoding="utf-8"))
    assert resumen[0]["tag"] == "X-1"
    assert (tmp_path / "salida" / "X-1" / "rev1" / "eventos.json").is_file()


def test_resumen_compartible_no_lleva_datos_del_plano():
    filas = [
        lote.Fila(
            "V-9001",
            "A",
            ["GAD_V-9001_revA.pdf"],
            "ok",
            familia="column",
            lod=2,
            boquillas=5,
            campos=30,
            pendientes=4,
            avisos=1,
            segundos=2.0,
            carpeta="/Volumes/tr/V-9001/revA",
        ),
        lote.Fila(
            "V-9001",
            "B",
            ["GAD_V-9001_revB.pdf"],
            "error",
            error="Falta el diámetro 2400 mm de V-9001",
            segundos=1.0,
        ),
        lote.Fila(
            "P-17",
            "1",
            ["GAD_P-17_rev1.pdf"],
            "error",
            error="ValueError: cota 1250 fuera de rango",
            segundos=3.0,
        ),
        lote.Fila(
            "P-17",
            "2",
            ["GAD_P-17_rev2.pdf"],
            "error",
            error="IFC inválido: IfcCartesianPoint 1250",
            segundos=4.0,
        ),
    ]
    resumen = lote.resumen_compartible(filas)
    texto = json.dumps(resumen, ensure_ascii=False)
    for secreto in ("V-9001", "P-17", "2400", "1250", "GAD_", "/Volumes", "diámetro"):
        assert secreto not in texto
    assert resumen["equipos"] == 2 and resumen["revisiones"] == 4
    assert resumen["estado"] == {"error": 3, "ok": 1}
    assert resumen["errores"] == {"ValueError": 1, "ifc_invalido": 1, "pipeline": 1}
    assert [r["equipo"] for r in resumen["por_revision"]] == ["E01", "E01", "E02", "E02"]
    assert resumen["segundos"] == {"total": 10.0, "mediana": 3.0, "max": 4.0}
