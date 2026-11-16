"""Evaluación de un lote contra IFC de referencia (G.1, G.3-G.5) con IFC propios disfrazados.

Las «referencias» son nuestros IFC con los nombres borrados, movidos y girados, como llegaría un
IFC de otro origen. Nunca datos de TR.
"""

import json
import random

import pytest

from bench.evaluar import (
    disfrazar,
    emparejar,
    evaluar,
    main,
    referencias_de_ensayo,
    resumen_compartible,
)
from synthetic.cases import random_case, spec_to_revision
from trazia.ifc import build_ifc


def _lote(tmp_path, revisiones: dict):
    """Salida de `trazia lote` mínima: resumen.json y <TAG>/rev<R>/{revision.json, modelo.ifc}."""
    salida = tmp_path / "salida"
    filas = []
    for tag, revision in revisiones.items():
        carpeta = salida / tag / "rev2"
        carpeta.mkdir(parents=True)
        (carpeta / "revision.json").write_text(revision.model_dump_json(), encoding="utf-8")
        (carpeta / "modelo.ifc").write_text(
            build_ifc(revision, draft=True).to_string(), encoding="utf-8"
        )
        filas.append({"tag": tag, "revision": "1", "estado": "error", "familia": None})
        filas.append({"tag": tag, "revision": "2", "estado": "ok", "familia": "vertical_vessel"})
    (salida / "resumen.json").write_text(json.dumps(filas), encoding="utf-8")
    return salida


@pytest.fixture(scope="module")
def specs():
    return {tag: random_case(random.Random(2026 + i), i) for i, tag in enumerate(("V-101", "V-7"))}


def _referencias(tmp_path, specs, cambio=None):
    carpeta = tmp_path / "referencias"
    carpeta.mkdir()
    for tag, spec in specs.items():
        revision = spec_to_revision(spec, "2")
        if cambio:
            cambio(tag, revision)
        modelo = disfrazar(build_ifc(revision, draft=True))
        modelo.write(str(carpeta / f"MODELO_{tag}_TR.ifc"))
    (carpeta / "MODELO_V-70.ifc").write_text("no casa con V-7", encoding="utf-8")
    return carpeta


def test_empareja_por_tag_completo(tmp_path):
    for nombre in ("V-101.ifc", "MODELO_V-7_rev1.IFC", "MODELO_V-7_rev2.ifc", "V-70.ifc", "x.txt"):
        (tmp_path / nombre).write_text("", encoding="utf-8")
    pares, notas, sueltos = emparejar(["V-101", "V-7", "P-1"], tmp_path)
    assert pares["V-101"].name == "V-101.ifc"
    assert pares["V-7"].name == "MODELO_V-7_rev2.ifc"  # V-70 no cuenta; se toma la última
    assert "P-1" not in pares and "V-7" in notas
    assert sueltos == 1


def test_un_lote_perfecto_da_error_cero_aunque_la_referencia_este_movida(tmp_path, specs):
    salida = _lote(tmp_path, {t: spec_to_revision(s, "2") for t, s in specs.items()})
    mapas = tmp_path / "mapas"
    evaluacion = evaluar(salida, _referencias(tmp_path, specs), muestras=600, mapas=mapas)
    assert [e["tag"] for e in evaluacion["equipos"]] == ["V-101", "V-7"]
    assert evaluacion["ifc_sin_equipo"] == 1
    for equipo in evaluacion["equipos"]:
        assert equipo["revision"] == "2"
        assert equipo["dimensiones"]["diameter"]["error_mm"] < 1
        assert equipo["boquillas"]["faltan"] == equipo["boquillas"]["sobran"] == 0
        assert equipo["boquillas"]["error_posicion_max_mm"] < 5
        # El giro de 90° se descubre con los otros equipos, no con el propio.
        assert equipo["convencion"]["exclusion"] == {"sign": 1, "offset": 90.0}
        assert equipo["convencion"]["estable"] is True
        assert equipo["convencion"]["cifra"] == "exclusion_de_uno"
        assert equipo["superficie"]["hausdorff_mm"] < 5
        assert equipo["superficie"]["iou_cajas"] > 0.99
        assert (mapas / f"mapa_{equipo['tag']}.html").stat().st_size > 1000
    assert evaluacion["agregado"]["boquillas"]["recall"] == 1.0


def test_un_diametro_mal_leido_se_ve_en_dimensiones_y_superficie(tmp_path, specs):
    salida = _lote(tmp_path, {t: spec_to_revision(s, "2") for t, s in specs.items()})

    def mas_ancho(tag, revision):
        if tag == "V-7":
            revision.equipment.diameter.value += 200.0

    evaluacion = evaluar(salida, _referencias(tmp_path, specs, mas_ancho), muestras=600)
    bien, mal = evaluacion["equipos"]
    assert mal["dimensiones"]["diameter"]["error_mm"] == pytest.approx(200, abs=1)
    assert mal["dimensiones"]["diameter"]["error_relativo"] == pytest.approx(
        200 / (specs["V-7"].diameter + 200), rel=0.01
    )
    assert mal["superficie"]["chamfer_mm"] > 20 > bien["superficie"]["chamfer_mm"]


def test_con_un_solo_equipo_la_cifra_queda_marcada_como_ajustada(tmp_path, specs):
    solo = {"V-101": specs["V-101"]}
    salida = _lote(tmp_path, {t: spec_to_revision(s, "2") for t, s in solo.items()})
    evaluacion = evaluar(salida, _referencias(tmp_path, solo), muestras=300)
    (equipo,) = evaluacion["equipos"]
    assert equipo["convencion"]["exclusion"] is None
    assert equipo["convencion"]["cifra"] == "ajustada_en_el_equipo"
    assert equipo["convencion"]["estable"] is False


def test_el_resumen_compartible_no_lleva_datos_del_equipo(tmp_path, specs):
    salida = _lote(tmp_path, {t: spec_to_revision(s, "2") for t, s in specs.items()})
    referencias = _referencias(tmp_path, specs)
    texto = json.dumps(resumen_compartible(evaluar(salida, referencias, muestras=300)))
    for prohibido in ("V-101", "V-7", "MODELO", ".ifc", str(tmp_path).replace("\\", "/")):
        assert prohibido not in texto
    datos = json.loads(texto)
    assert [e["equipo"] for e in datos["por_equipo"]] == ["E01", "E02"]
    assert "error_mm_mediano" not in datos["agregado"]
    assert "reference" not in texto and "sesgo_cota" not in texto
    assert datos["equipos_con_referencia"] == 2


def test_cli_escribe_el_json_completo(tmp_path, specs, capsys):
    solo = {"V-101": specs["V-101"]}
    salida = _lote(tmp_path, {t: spec_to_revision(s, "2") for t, s in solo.items()})
    destino = tmp_path / "evaluacion.json"
    codigo = main(
        [str(salida), str(_referencias(tmp_path, solo)), "--muestras", "200", "-o", str(destino)]
    )
    assert codigo == 0
    assert json.loads(destino.read_text(encoding="utf-8"))["equipos"][0]["tag"] == "V-101"
    assert '"equipos"' in capsys.readouterr().out


def test_referencias_de_ensayo_salen_del_propio_lote(tmp_path, specs):
    salida = _lote(tmp_path, {t: spec_to_revision(s, "2") for t, s in specs.items()})
    destino = tmp_path / "ensayo"
    assert referencias_de_ensayo(salida, destino) == 2
    evaluacion = evaluar(salida, destino, muestras=300)
    assert len(evaluacion["equipos"]) == 2
    assert all(e["superficie"]["hausdorff_mm"] < 5 for e in evaluacion["equipos"])
