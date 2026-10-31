"""Proveedores de visión: Ollama local, Gemini y Mistral (DEC-03).

Todos comparten `_cached_call`: caché, modo sin conexión, política de confidencialidad y registro
de envíos. Solo cambia cómo se habla con cada servicio y cómo devuelve las cajas. HTTP con la
biblioteca estándar: sin dependencias nuevas.

`page_ref` identifica la imagen para el registro: `<sha256 del documento>#p<página>[/t<mosaico>]`.
"""

import base64
import ipaddress
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from urllib.parse import urlsplit

from . import cache, policy
from .base import ProviderResult, VisionError, VisionUnavailable
from .prompts import TASKS, validate


def _post(url: str, payload: dict, headers: dict | None = None, timeout: float = 600) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise VisionError(f"{url}: HTTP {exc.code} {detail}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise VisionUnavailable(f"{url}: {exc}") from None


def _get(url: str, key: str, timeout: float = 60) -> dict:
    """GET con clave, sin seguir redirecciones (la clave no sale hacia otro sitio)."""
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise VisionError(f"{url}: HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise VisionUnavailable(f"{url}: {exc}") from None


def _scale_boxes(data, factor: float = 1000.0):
    """Cajas 0–1000 → 0–1, recortadas a la imagen y ordenadas (x0 ≤ x1, y0 ≤ y1)."""
    if isinstance(data, dict):
        out = {}
        for key, value in data.items():
            if key in ("bbox", "box_2d") and isinstance(value, list) and len(value) == 4:
                x0, y0, x1, y1 = (min(1.0, max(0.0, float(v) / factor)) for v in value)
                out["bbox"] = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
            else:
                out[key] = _scale_boxes(value, factor)
        return out
    if isinstance(data, list):
        return [_scale_boxes(item, factor) for item in data]
    return data


class _Provider:
    name: str
    model: str
    external: bool

    def __init__(self, *, dataset: str = "synthetic"):
        self.dataset = dataset

    def _call(self, image_png: bytes, prompt: str, schema: dict) -> tuple[dict, dict]:
        raise NotImplementedError

    def read(self, image_png: bytes, task: str, schema: dict | None = None, *, page_ref: str):
        spec = TASKS[task]
        schema = schema or spec.schema
        key = cache.cache_key(
            image_png, spec.prompt_sha256, schema, getattr(self, "cache_identity", self.name)
        )
        hit = cache.load(key)
        if hit is not None:
            return hit
        if cache.offline():
            raise VisionUnavailable(f"{self.name}: modo sin conexión y sin respuesta en caché")
        document_sha = page_ref.split("#", 1)[0]
        policy.guard_and_log(
            self.name,
            external=self.external,
            dataset=self.dataset,
            document_sha256=document_sha,
            page_ref=page_ref,
        )
        started = time.perf_counter()
        data, usage = self._call(image_png, spec.prompt, schema)
        errors = validate(data, schema)
        if errors:
            raise VisionError(f"{self.name}: respuesta fuera de esquema: {'; '.join(errors[:3])}")
        result = ProviderResult(
            data=_scale_boxes(data),
            provider=self.name,
            model=self.model,
            prompt_sha256=spec.prompt_sha256,
            seconds=usage.get("seconds", time.perf_counter() - started),
            tokens_in=usage.get("tokens_in"),
            tokens_out=usage.get("tokens_out"),
            cost_eur=usage.get("cost_eur", 0.0),
            external=self.external,
        )
        cache.store(key, result)
        return result


class OllamaProvider(_Provider):
    """Modelo local servido por Ollama. No sale nada del equipo; coste 0 €."""

    external = False

    def __init__(
        self, model: str = "qwen3-vl:4b-instruct", *, dataset: str = "synthetic", host=None
    ):
        super().__init__(dataset=dataset)
        self.model = model or os.environ.get("TRAZIA_OLLAMA_MODEL", "qwen3-vl:4b-instruct")
        self.name = f"ollama:{self.model}"
        self.host = (
            host
            or os.environ.get("TRAZIA_OLLAMA_URL")
            or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        ).rstrip("/")
        if not self.host.startswith("http"):
            self.host = f"http://{self.host}"
        url = urlsplit(self.host)
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
        ):
            raise VisionUnavailable("Ollama: URL de servicio inválida")
        try:
            local = ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            local = url.hostname in ("localhost", "ollama", "host.docker.internal")
        self.external = not local
        self.cache_identity = f"{self.name}@{self.host}"

    def _call(self, image_png, prompt, schema):
        details = _post(f"{self.host}/api/show", {"model": self.model})
        if details.get("remote_host") or details.get("remote_model"):
            raise VisionUnavailable("Ollama: se requieren pesos locales, sin modelo cloud")
        if details.get("details", {}).get("format") != "gguf" or "vision" not in details.get(
            "capabilities", []
        ):
            raise VisionUnavailable("Ollama: no se pudo verificar un modelo visual local")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64.b64encode(image_png).decode("ascii")],
                }
            ],
            "format": schema,
            "stream": False,
            "think": False,
            "keep_alive": "15m",
            "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 4096},
        }
        response = _post(f"{self.host}/api/chat", payload)
        try:
            data = json.loads(response["message"]["content"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise VisionError(f"{self.name}: respuesta no es JSON ({exc})") from None
        return data, {
            "seconds": response.get("total_duration", 0) / 1e9,
            "tokens_in": response.get("prompt_eval_count"),
            "tokens_out": response.get("eval_count"),
            "cost_eur": 0.0,
        }


def _price(env: str, default: float) -> float:
    """Precio en € por millón de tokens, configurable porque cambia: revisar antes del pitch."""
    try:
        return float(os.environ.get(env, default))
    except ValueError:
        return default


class GeminiProvider(_Provider):
    """Gemini con salida JSON por esquema. Externo: solo sintéticos salvo autorización."""

    external = True

    def __init__(self, model: str | None = None, *, dataset: str = "synthetic"):
        super().__init__(dataset=dataset)
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.name = f"gemini:{self.model}"
        self.key = os.environ.get("GEMINI_API_KEY")
        if not self.key and not cache.offline():
            raise VisionUnavailable("Gemini: falta GEMINI_API_KEY en .env")

    def _call(self, image_png, prompt, schema):
        if not self.key:
            raise VisionUnavailable("Gemini: falta GEMINI_API_KEY")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(image_png).decode("ascii"),
                            }
                        },
                        {"text": prompt},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": _gemini_schema(schema),
            },
        }
        response = _post(url, payload, {"x-goog-api-key": self.key})
        try:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise VisionError(f"{self.name}: respuesta inesperada ({exc})") from None
        usage = response.get("usageMetadata", {})
        tokens_in, tokens_out = usage.get("promptTokenCount"), usage.get("candidatesTokenCount")
        cost = (tokens_in or 0) / 1e6 * _price("GEMINI_EUR_PER_MTOK_IN", 0.30) + (
            tokens_out or 0
        ) / 1e6 * _price("GEMINI_EUR_PER_MTOK_OUT", 2.30)
        return data, {"tokens_in": tokens_in, "tokens_out": tokens_out, "cost_eur": cost}


def _gemini_schema(schema: dict) -> dict:
    """Gemini acepta un subconjunto de OpenAPI: sin minItems/maxItems en algunos modelos."""
    out = {k: v for k, v in schema.items() if k not in ("minItems", "maxItems")}
    if "properties" in out:
        out["properties"] = {k: _gemini_schema(v) for k, v in out["properties"].items()}
    if "items" in out:
        out["items"] = _gemini_schema(out["items"])
    return out


class MistralOCRProvider(_Provider):
    """Mistral OCR: texto y cajas por bloque. Externo: solo sintéticos salvo autorización.

    Solo sirve la tarea «lineas»; la conversión a líneas con caja usa las imágenes y bloques que
    devuelve el servicio. Precio aproximado por página, configurable.
    """

    external = True

    def __init__(self, model: str | None = None, *, dataset: str = "synthetic"):
        super().__init__(dataset=dataset)
        self.model = model or os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
        self.name = f"mistral-ocr:{self.model}"
        self.key = os.environ.get("MISTRAL_API_KEY")
        if not self.key and not cache.offline():
            raise VisionUnavailable("Mistral: falta MISTRAL_API_KEY en .env")

    def read(self, image_png, task, schema=None, *, page_ref):
        if task != "lineas":
            raise VisionError("Mistral OCR solo implementa la tarea «lineas»")
        return super().read(image_png, task, schema, page_ref=page_ref)

    def _call(self, image_png, prompt, schema):
        if not self.key:
            raise VisionUnavailable("Mistral: falta MISTRAL_API_KEY")
        payload = {
            "model": self.model,
            "document": {
                "type": "image_url",
                "image_url": "data:image/png;base64," + base64.b64encode(image_png).decode(),
            },
            "include_image_base64": False,
            "include_blocks": True,
        }
        response = _post(
            "https://api.mistral.ai/v1/ocr", payload, {"Authorization": f"Bearer {self.key}"}
        )
        items = []
        for page in response.get("pages", []):
            dims = page.get("dimensions") or {}
            width, height = dims.get("width"), dims.get("height")
            if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
                raise VisionError("Mistral: página sin dimensiones para normalizar cajas")
            if width <= 0 or height <= 0:
                raise VisionError("Mistral: dimensiones de página inválidas")
            for block in page.get("blocks", []) or []:
                keys = ("top_left_x", "top_left_y", "bottom_right_x", "bottom_right_y")
                box = (
                    [block[k] for k in keys]
                    if all(k in block for k in keys)
                    else block.get("bbox") or block.get("bounding_box")
                )
                if not box or len(box) != 4:
                    continue
                x0, y0, x1, y1 = box
                items.append(
                    {
                        "text": block.get("content", block.get("text", "")),
                        "bbox": [
                            x0 / width * 1000,
                            y0 / height * 1000,
                            x1 / width * 1000,
                            y1 / height * 1000,
                        ],
                    }
                )
        pages = len(response.get("pages", [])) or 1
        cost = pages * _price("MISTRAL_EUR_PER_PAGE", 0.004)
        return {"items": items}, {"cost_eur": cost}


# € por millón de tokens (entrada, salida) de los modelos de chat de Mistral con visión.
# Aproximados y configurables con MISTRAL_EUR_PER_MTOK_IN/OUT: revisar antes del pitch.
MISTRAL_PRICES = {
    "mistral-small": (0.1, 0.3),
    "mistral-medium": (0.4, 2.0),
    "pixtral-12b": (0.15, 0.15),
    "pixtral-large": (2.0, 6.0),
    "mistral-large": (2.0, 6.0),
}


class MistralChatProvider(_Provider):
    """Modelos de chat de Mistral con visión (Pixtral, Small, Medium, Large) con salida JSON por
    esquema. Externo: solo sintéticos salvo autorización (DEC-03)."""

    external = True

    def __init__(self, model: str | None = None, *, dataset: str = "synthetic"):
        super().__init__(dataset=dataset)
        self.model = model or os.environ.get("MISTRAL_CHAT_MODEL", "mistral-small-latest")
        self.name = f"mistral-chat:{self.model}"
        self.key = os.environ.get("MISTRAL_API_KEY")
        if not self.key and not cache.offline():
            raise VisionUnavailable("Mistral: falta MISTRAL_API_KEY en .env")

    def _call(self, image_png, prompt, schema):
        if not self.key:
            raise VisionUnavailable("Mistral: falta MISTRAL_API_KEY")
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": "data:image/png;base64,"
                            + base64.b64encode(image_png).decode("ascii"),
                        },
                    ],
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "lectura", "schema": schema, "strict": True},
            },
        }
        started = time.perf_counter()
        response = _post(
            "https://api.mistral.ai/v1/chat/completions",
            payload,
            {"Authorization": f"Bearer {self.key}"},
        )
        try:
            data = json.loads(response["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise VisionError(f"{self.name}: respuesta inesperada ({exc})") from None
        usage = response.get("usage", {})
        tokens_in, tokens_out = usage.get("prompt_tokens"), usage.get("completion_tokens")
        family = next((f for f in MISTRAL_PRICES if self.model.startswith(f)), None)
        price_in, price_out = MISTRAL_PRICES.get(family, (2.0, 6.0))
        cost = (tokens_in or 0) / 1e6 * _price("MISTRAL_EUR_PER_MTOK_IN", price_in) + (
            tokens_out or 0
        ) / 1e6 * _price("MISTRAL_EUR_PER_MTOK_OUT", price_out)
        return data, {
            "seconds": time.perf_counter() - started,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_eur": cost,
        }


FACTORIES: dict[str, Callable[..., _Provider]] = {
    "ollama": OllamaProvider,
    "gemini": GeminiProvider,
    "mistral-ocr": MistralOCRProvider,
    "mistral": MistralOCRProvider,
    "mistral-chat": MistralChatProvider,
}


def get_provider(spec: str, *, dataset: str = "synthetic") -> _Provider:
    """«ollama:qwen3-vl:4b», «gemini», «gemini:gemini-2.5-flash», «mistral»…"""
    family, _, model = spec.partition(":")
    if family == "plataforma":
        raise VisionUnavailable("Plataforma IndesIA: se conocerá en la formación del día 1")
    if family not in FACTORIES:
        raise VisionError(f"Proveedor de visión desconocido: {spec}")
    return FACTORIES[family](model or None, dataset=dataset)
