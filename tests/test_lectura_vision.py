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


def test_versioned_qwen_answer_reads_the_synthetic_ga(monkeypatch):
    monkeypatch.setenv("TRAZIA_VISION_CACHE", str(FIXTURES))
    monkeypatch.setenv("TRAZIA_VISION_OFFLINE", "1")
    image = (FIXTURES / "ga_v101.png").read_bytes()
    result = OllamaProvider("qwen3-vl:4b-instruct").read(image, "lineas", page_ref="fixture#p1/t0")
    texts = [item["text"] for item in result.data["items"]]
    assert "DIAMETER = 2000 mm" in texts
    assert any("NOZZLE SCHEDULE" in text for text in texts)
    assert all(0 <= v <= 1 for item in result.data["items"] for v in item["bbox"])


@pytest.mark.parametrize("family", ["gemini", "mistral"])
def test_real_adapters_share_schema_and_replay_without_credentials(isolated, monkeypatch, family):
    from trazia.vision import providers

    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-only")
    requests = []

    def post(url, payload, headers=None):
        requests.append((url, payload))
        if "googleapis" in url:
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "items": [
                                                # Gemini: [y1, x1, y2, x2]
                                                {"text": "ID 2000", "bbox": [200, 100, 260, 300]}
                                            ]
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 10},
            }
        assert payload["include_blocks"] is True
        return {
            "pages": [
                {
                    "dimensions": {"width": 2000, "height": 1000},
                    "blocks": [
                        {
                            "type": "text",
                            "content": "ID 2000",
                            "top_left_x": 200,
                            "top_left_y": 200,
                            "bottom_right_x": 600,
                            "bottom_right_y": 260,
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(providers, "_post", post)
    provider = providers.get_provider(family)
    answer = provider.read(b"synthetic", "lineas", page_ref="doc#p1")
    assert answer.data == {"items": [{"text": "ID 2000", "bbox": [0.1, 0.2, 0.3, 0.26]}]}
    assert len(requests) == 1 and len(_log(isolated)) == 1
    monkeypatch.setenv("TRAZIA_VISION_OFFLINE", "1")
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("MISTRAL_API_KEY")
    replay = providers.get_provider(family).read(b"synthetic", "lineas", page_ref="doc#p1")
    assert replay.cached and replay.data == answer.data
    assert len(requests) == 1 and len(_log(isolated)) == 1


def test_mistral_missing_dimensions_does_not_invent_page_boxes(isolated, monkeypatch):
    from trazia.vision import providers

    monkeypatch.setenv("MISTRAL_API_KEY", "test-only")
    monkeypatch.setattr(providers, "_post", lambda *a: {"pages": [{"markdown": "ID 2000"}]})
    with pytest.raises(VisionError, match="dimensiones"):
        providers.get_provider("mistral").read(b"synthetic", "lineas", page_ref="doc#p1")


def test_ollama_remote_is_external_and_cloud_cannot_receive_an_image(isolated, monkeypatch):
    from trazia.vision import providers

    calls = []

    def post(url, payload, headers=None):
        calls.append(payload)
        return {"remote_host": "https://example.invalid", "remote_model": "cloud"}

    monkeypatch.setattr(providers, "_post", post)
    remote = providers.OllamaProvider(host="http://192.0.2.1:11434", dataset="real")
    assert remote.external
    with pytest.raises(PolicyError):
        remote.read(b"private", "lineas", page_ref="doc#p1")
    assert not calls
    local = providers.OllamaProvider(host="http://localhost:11434")
    with pytest.raises(VisionUnavailable, match="cloud"):
        local.read(b"synthetic", "lineas", page_ref="doc#p1")
    assert calls == [{"model": "qwen3-vl:4b-instruct"}]


def test_ollama_default_and_compose_environment_are_consistent(isolated, monkeypatch):
    from trazia.vision.providers import get_provider

    monkeypatch.setenv("TRAZIA_OLLAMA_URL", "http://ollama:11434")
    monkeypatch.setenv("TRAZIA_OLLAMA_MODEL", "qwen3-vl:4b-instruct")
    provider = get_provider("ollama")
    assert provider.model == "qwen3-vl:4b-instruct" and provider.host == "http://ollama:11434"
    assert not provider.external


def test_comparison_requires_distinct_families_and_reports_missing_provider(isolated, monkeypatch):
    from trazia.vision import comparar

    image = isolated / "page.png"
    Image.new("RGB", (100, 100), "white").save(image)

    def provider(spec, **kwargs):
        if spec == "missing":
            raise VisionUnavailable("falta credencial de prueba")
        value = FakeProvider(external=False)
        value.name = spec
        return value

    monkeypatch.setattr(comparar, "get_provider", provider)
    output = isolated / "comparison.json"
    assert (
        comparar.main(
            [
                str(image),
                "--proveedores",
                "ollama:a",
                "ollama:b",
                "missing",
                "--salida",
                str(output),
            ]
        )
        == 2
    )
    data = json.loads(output.read_text(encoding="utf8"))
    assert not data["complete"] and data["distinct_providers"] == 1
    assert data["results"][0]["offline_replay"] and not data["results"][2]["success"]
    assert (
        comparar.main(
            [str(image), "--proveedores", "ollama:a", "gemini:b", "--salida", str(output)]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf8"))["distinct_providers"] == 2


def test_mistral_chat_reads_lines_with_schema_cost_and_offline_replay(isolated, monkeypatch):
    from trazia.vision import providers

    monkeypatch.setenv("MISTRAL_API_KEY", "test-only")
    requests = []

    def post(url, payload, headers=None):
        requests.append((url, payload))
        content = json.dumps({"items": [{"text": "ID 2000", "bbox": [100, 200, 300, 260]}]})
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0},
        }

    monkeypatch.setattr(providers, "_post", post)
    provider = providers.get_provider("mistral-chat:mistral-small-latest")
    answer = provider.read(b"synthetic", "lineas", page_ref="doc#p1")
    url, payload = requests[0]
    assert url.endswith("/v1/chat/completions") and payload["model"] == "mistral-small-latest"
    assert payload["response_format"]["json_schema"]["schema"]["required"] == ["items"]
    assert answer.data["items"][0]["bbox"] == [0.1, 0.2, 0.3, 0.26]
    assert answer.external and answer.cost_eur == pytest.approx(0.1)
    with pytest.raises(PolicyError):
        providers.get_provider("mistral-chat", dataset="real").read(
            b"private", "lineas", page_ref="doc#p2"
        )
    monkeypatch.setenv("TRAZIA_VISION_OFFLINE", "1")
    monkeypatch.delenv("MISTRAL_API_KEY")
    replay = providers.get_provider("mistral-chat:mistral-small-latest").read(
        b"synthetic", "lineas", page_ref="doc#p1"
    )
    assert replay.cached and len(requests) == 1


def test_openai_compatible_services_fall_back_on_json_mode_and_retry(isolated, monkeypatch):
    from trazia.vision import providers

    for env in ("GROQ_API_KEY", "CLOUDFLARE_API_TOKEN"):
        monkeypatch.setenv(env, "test-only")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "cuenta")
    monkeypatch.setattr(providers, "RETRY_WAITS", (0,))
    requests = []

    def post(url, payload, headers=None):
        requests.append((url, payload))
        if len(requests) == 1:
            raise VisionError(f"{url}: HTTP 429 cuota")  # se reintenta
        if payload.get("response_format", {}).get("type") == "json_schema":
            raise VisionError(f"{url}: HTTP 400 response_format no admitido")
        content = '<think>leo la tabla</think>```json\n{"items": [{"text": "ID 2000", '
        content += '"bbox": [100, 200, 300, 260]}]}\n```'
        return {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 10}}

    monkeypatch.setattr(providers, "_post", post)
    groq = providers.get_provider("groq:qwen/qwen3.8-27b")
    answer = groq.read(b"synthetic", "lineas", page_ref="doc#p1")
    assert answer.data["items"][0]["bbox"] == [0.1, 0.2, 0.3, 0.26]
    assert answer.external and answer.cost_eur == 0.0 and groq.mode == 1
    assert [p.get("response_format", {}).get("type") for _, p in requests] == [
        "json_schema",
        "json_schema",
        "json_object",
    ]
    _, payload = requests[-1]
    text = payload["messages"][0]["content"][0]["text"]
    assert "JSON Schema of the answer" in text  # sin esquema estricto, va en el prompt
    assert payload["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png")
    cloudflare = providers.get_provider("cloudflare:@cf/qwen/qwen3.8-27b")
    assert cloudflare.url.endswith("/accounts/cuenta/ai/v1/chat/completions")
    with pytest.raises(PolicyError):
        providers.get_provider("groq", dataset="real").read(b"x", "lineas", page_ref="d#p2")
    monkeypatch.delenv("GROQ_API_KEY")
    with pytest.raises(VisionUnavailable):
        providers.get_provider("groq")
