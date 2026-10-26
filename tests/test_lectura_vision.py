"""Visión: política de confidencialidad, registro de envíos, caché, modo sin conexión y mosaicos.

Ningún modelo corre aquí: un proveedor falso responde y las respuestas reales de Qwen3-VL van
versionadas en tests/fixtures/vision_cache/.
"""

import json
from pathlib import Path

import pytest
from PIL import Image

from trazia.vision import PolicyError, VisionError, VisionUnavailable
from trazia.vision.providers import OllamaProvider, _Provider
from trazia.vision.reader import read_page
from trazia.vision.tiling import Tile, merge_duplicates, tiles

FIXTURES = Path(__file__).parent / "fixtures" / "vision_cache"


class FakeProvider(_Provider):
    """Responde como un modelo: cajas 0–1000 sobre la imagen recibida."""

    def __init__(self, *, external: bool, dataset: str = "synthetic", answer=None):
        super().__init__(dataset=dataset)
        self.external = external
        self.model = "fake"
        self.name = "fake:model"
        self.calls = 0
        self.answer = answer or {"items": [{"text": "ID 2000", "bbox": [100, 200, 300, 260]}]}

    def _call(self, image_png, prompt, schema):
        self.calls += 1
        return self.answer, {"tokens_in": 10, "tokens_out": 5, "cost_eur": 0.001}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAZIA_VISION_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("TRAZIA_REGISTRO_ENVIOS", str(tmp_path / "registro.jsonl"))
    monkeypatch.delenv("TRAZIA_VISION_OFFLINE", raising=False)
    monkeypatch.delenv("TRAZIA_EXTERNAL_PROVIDERS", raising=False)
    monkeypatch.delenv("TRAZIA_EXTERNAL_AUTH", raising=False)
    return tmp_path


def _log(tmp_path) -> list[dict]:
    path = tmp_path / "registro.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_boxes_are_normalised_and_responses_cached(isolated):
    provider = FakeProvider(external=False)
    first = provider.read(b"png", "lineas", page_ref="abc#p1")
    assert first.data["items"][0]["bbox"] == [0.1, 0.2, 0.3, 0.26]
    second = provider.read(b"png", "lineas", page_ref="abc#p1")
    assert provider.calls == 1 and second.cached and second.data == first.data
    assert first.prompt_sha256 and not _log(isolated)  # local: no se registra envío


def test_offline_mode_never_calls_the_model(isolated, monkeypatch):
    monkeypatch.setenv("TRAZIA_VISION_OFFLINE", "1")
    provider = FakeProvider(external=False)
    with pytest.raises(VisionUnavailable):
        provider.read(b"otra", "lineas", page_ref="abc#p1")
    assert provider.calls == 0


def test_schema_violations_are_rejected(isolated):
    provider = FakeProvider(external=False, answer={"items": [{"text": "x", "bbox": [1, 2]}]})
    with pytest.raises(VisionError, match="esquema"):
        provider.read(b"png", "lineas", page_ref="abc#p1")


def test_default_policy_allows_external_only_with_synthetic_data(isolated):
    FakeProvider(external=True).read(b"png", "lineas", page_ref="sha-doc#p2")
    [entry] = _log(isolated)
    assert entry["provider"] == "fake:model" and entry["document_sha256"] == "sha-doc"
    assert entry["page"] == "sha-doc#p2" and entry["dataset"] == "synthetic"
    real = FakeProvider(external=True, dataset="real")
    with pytest.raises(PolicyError, match="reales"):
        real.read(b"png2", "lineas", page_ref="sha-real#p1")
    assert real.calls == 0 and len(_log(isolated)) == 1


def test_deny_and_allow_policies(isolated, monkeypatch):
    monkeypatch.setenv("TRAZIA_EXTERNAL_PROVIDERS", "deny")
    with pytest.raises(PolicyError):
        FakeProvider(external=True).read(b"png", "lineas", page_ref="s#p1")
    monkeypatch.setenv("TRAZIA_EXTERNAL_PROVIDERS", "allow")
    real = FakeProvider(external=True, dataset="real")
    with pytest.raises(PolicyError, match="TRAZIA_EXTERNAL_AUTH"):
        real.read(b"png", "lineas", page_ref="s#p1")
    monkeypatch.setenv("TRAZIA_EXTERNAL_AUTH", "correo del mentor, 25/11/2026")
    real.read(b"png", "lineas", page_ref="s#p1")
    assert _log(isolated)[-1]["authorization"] == "correo del mentor, 25/11/2026"
    # Un proveedor local nunca pasa por la política: los datos no salen del equipo.
    monkeypatch.setenv("TRAZIA_EXTERNAL_PROVIDERS", "deny")
    FakeProvider(external=False, dataset="real").read(b"png3", "lineas", page_ref="s#p1")


def test_tiles_cover_the_page_with_overlap_and_reproject():
    page = Image.new("L", (3000, 2000), 255)
    parts = tiles(page, size=1280, overlap=0.15)
    assert len(parts) == 6
    assert parts[0].box[0] == 0 and parts[-1].box[2] == 1 and parts[-1].box[3] == 1
    tile = Tile(page, (0.5, 0.5, 1.0, 1.0))
    assert tile.to_page((0.0, 0.0, 0.5, 0.5)) == (0.5, 0.5, 0.75, 0.75)
    merged = merge_duplicates(
        [
            {"text": "2000", "box": (0.10, 0.10, 0.20, 0.12)},
            {"text": "2000", "box": (0.10, 0.10, 0.19, 0.12)},  # el mismo, en el solape
            {"text": "2000", "box": (0.60, 0.60, 0.70, 0.62)},  # otro 2000 en otro sitio
        ]
    )
    assert len(merged) == 2


def test_read_page_keeps_going_when_a_tile_fails(isolated):
    class Flaky(FakeProvider):
        attempts = 0

        def _call(self, image_png, prompt, schema):
            self.attempts += 1
            if self.attempts == 2:
                raise VisionError("tiempo agotado")
            return super()._call(image_png, prompt, schema)

    page = (
        Image.linear_gradient("L").rotate(90).resize((2400, 1200)).convert("RGB")
    )  # mosaicos distintos
    reading = read_page(Flaky(external=False), page, page_ref="doc#p1", tile_size=1280)
    assert reading.tiles == 3 and len(reading.errors) == 1
    assert reading.items and all(0 <= v <= 1 for v in reading.items[0]["bbox"])


@pytest.mark.skipif(not FIXTURES.exists(), reason="sin respuestas versionadas")
def test_versioned_qwen_answer_reads_the_nozzle_table(monkeypatch):
    monkeypatch.setenv("TRAZIA_VISION_CACHE", str(FIXTURES))
    monkeypatch.setenv("TRAZIA_VISION_OFFLINE", "1")
    image = (FIXTURES / "tabla_boquillas.png").read_bytes()
    result = OllamaProvider("qwen3-vl:4b-instruct").read(image, "lineas", page_ref="fixture#p1/t0")
    texts = [item["text"] for item in result.data["items"]]
    assert "NOZZLE SCHEDULE" in texts and "12350" in texts
    assert all(0 <= v <= 1 for item in result.data["items"] for v in item["bbox"])
