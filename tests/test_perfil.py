"""Perfil del dataset: recuentos útiles y ningún nombre, tag ni texto de los documentos."""

import io
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from trazia.cli import main
from trazia.ingest import image_to_pdf
from trazia.perfil import avisos, forma, perfilar

EJEMPLOS = Path(__file__).resolve().parents[1] / "examples" / "documents"


def _carpeta(tmp_path):
    entrada = tmp_path / "Volumes" / "indesia" / "datos"
    (entrada / "planos").mkdir(parents=True)
    for path in EJEMPLOS.iterdir():
        shutil.copy(path, entrada / "planos" / path.name)
    imagen = Image.new("RGB", (1240, 877), "white")
    ImageDraw.Draw(imagen).rectangle((100, 100, 1100, 700), outline="black", width=4)
    png = io.BytesIO()
    imagen.save(png, format="PNG", dpi=(150, 150))
    (entrada / "planos" / "GAD_P-2001A_rev1.pdf").write_bytes(image_to_pdf(png.getvalue()))
    (entrada / "planos" / "VESOR_P-2001A.png").write_bytes(png.getvalue())
    (entrada / "planos" / "copia de GAD_V-101_revA.pdf").write_bytes(
        (EJEMPLOS / "GAD_V-101_revA.pdf").read_bytes()
    )
    (entrada / "Notas cliente Cartagena 2024.docx").write_bytes(b"PK\x03\x04")
    (entrada / "GAD_X-9_rev1.pdf").write_bytes(b"%PDF-1.4 roto")
    (entrada / "V-101_TR.ifc").write_text(
        "ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nENDSEC;\n", encoding="utf-8"
    )
    return entrada


def test_forma_reduce_nombres_sin_perder_la_estructura():
    assert forma("GAD_V-101_revA") == "GAD_A-9_revA"
    assert forma("HDM_10-P-2001A_rev12") == "HDM_9-A-9A_rev9"
    assert forma("Notas cliente Cartagena 2024") == "A A A 9"


def test_perfil_cuenta_lo_que_importa(tmp_path):
    perfil = perfilar(_carpeta(tmp_path))
    archivos, equipos, pdf = perfil["archivos"], perfil["equipos"], perfil["pdf"]
    assert archivos["total"] == 10
    assert archivos["por_extension"][".pdf"] == 5
    assert archivos["duplicados_exactos"] == 1
    assert sum(archivos["errores_de_lectura"].values()) == 1  # el PDF roto, por su categoría
    assert archivos["formas_fuera_del_reto"] == {"A A A 9.docx": 1, "A A GAD_A-9_revA.pdf": 1}
    assert equipos["total"] == 3
    assert equipos["revisiones_por_equipo"] == {1: 2, 2: 1}
    assert equipos["forma_de_tag"]["A-9"] >= 4
    assert equipos["sin_revision_por_tipo"] == {"VESOR": 1}
    assert equipos["sin_ga"] == 0
    assert pdf["clase"]["vectorial"] == 3  # los dos ejemplos y su copia
    assert pdf["clase"]["escaneado"] == 1
    assert perfil["imagenes"] == {
        "documentos": 1,
        "megapixeles": {"n": 1, "min": 1.09, "mediana": 1.09, "max": 1.09},
        "dpi": {150: 1},
        "multipagina": 0,
    }
    assert perfil["xlsx"]["documentos"] == 2
    assert perfil["ifc"] == {"archivos": 1, "esquema": {"IFC4": 1}, "con_equipo_del_lote": 1}
    assert perfil["contenido"]["documentos_con_texto"] >= 4
    assert perfil["contenido"]["documentos_con_patron"].get("marca_boquilla", 0) >= 1
    lecturas = " ".join(avisos(perfil))
    assert "escaneados" in lecturas and "no siguen" in lecturas and "03_evaluar" in lecturas


def test_perfil_no_lleva_nombres_tags_ni_rutas(tmp_path):
    entrada = _carpeta(tmp_path)
    perfil = perfilar(entrada)
    texto = json.dumps({**perfil, "avisos": avisos(perfil)}, ensure_ascii=False)
    for prohibido in ("V-101", "P-2001A", "X-9", "Cartagena", "cliente", "Volumes", "planos"):
        assert prohibido not in texto, prohibido


def test_cli_perfil(tmp_path, capsys):
    entrada = _carpeta(tmp_path)
    assert main(["perfil", str(entrada), "--max-paginas", "2"]) == 0
    datos = json.loads(capsys.readouterr().out)
    assert datos["equipos"]["total"] == 3 and datos["avisos"]
