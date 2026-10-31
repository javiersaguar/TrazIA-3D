"""Calibración de la confianza, intervalos conformes y abstención (tarea 3.3).

Etapa `calibrate` de `trazia.pipeline.process`, entre la reconciliación y el contrato:

1. Confianza: curva isotónica por (estrategia, canal, tipo de documento), con respaldo por
   (estrategia, canal), por estrategia, por canal y global. El tipo es `scan` para un PDF sin capa
   de texto y `vector` para el resto: el mismo canal acierta mucho menos sobre un escaneado.
   La confianza de la estrategia pasa a `source.confidence_raw` y la calibrada a
   `source.confidence`.
2. Intervalo conforme al 90 % para cada campo numérico (ver `conformal.py`).
3. Abstención: por debajo del umbral de la estrategia, o si su intervalo al 90 % no informa, el
   campo queda `abstained`. El valor se conserva para la revisión, pero no se puede aprobar sin
   que una persona lo confirme.

Los parámetros se ajustan con `uv run python -m bench.calibrar` (S-dev) y se guardan en
`generated/calibration/calibracion.json`. Otra ruta: `TRAZIA_CALIBRATION`; `off` la desactiva.
Sin parámetros la etapa queda omitida y la confianza sale tal como la da la estrategia.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from ..extraction import Candidate, Interval
from . import conformal
from .isotonic import apply_curve

FORMAT = 1
DEFAULT_PATH = "generated/calibration/calibracion.json"


def calibration_path() -> Path | None:
    value = os.environ.get("TRAZIA_CALIBRATION", DEFAULT_PATH).strip()
    if value.lower() in ("", "0", "off", "no"):
        return None
    return Path(value)


def _es(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def _base(strategy: str) -> str:
    """`d_hibrido-memoria` → `d_hibrido`: una ablación usa la curva de su estrategia si no tiene."""
    return strategy.split("-")[0]


@dataclass
class Calibration:
    curves: dict[str, dict]  # "estrategia|canal|tipo" o "estrategia|canal" → curva; "*" comodín
    # "clase|franja", "clase|*" y "estrategia|clase|franja" → cuantil conforme
    quantiles: dict[str, float]
    thresholds: dict[str, float]  # estrategia o "*" → umbral de abstención
    level: float = conformal.LEVEL
    fitted_on: str = ""
    meta: dict = field(default_factory=dict)
    # Estrategias cuya confianza ya es una probabilidad ajustada en S-dev (fusión aprendida, 3.4):
    # no pasan por la curva isotónica; sí reciben intervalo y umbral de abstención.
    passthrough: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Calibration":
        if data.get("format") != FORMAT:
            raise ValueError(f"Formato de calibración no admitido: {data.get('format')}")
        return cls(
            curves=data["curves"],
            quantiles=data["quantiles"],
            thresholds=data["thresholds"],
            level=data["level"],
            fitted_on=data.get("fitted_on", ""),
            meta=data.get("meta", {}),
            passthrough=list(data.get("passthrough", [])),
        )

    def to_dict(self) -> dict:
        out = {
            "format": FORMAT,
            "level": self.level,
            "fitted_on": self.fitted_on,
            "curves": self.curves,
            "quantiles": self.quantiles,
            "thresholds": self.thresholds,
            "meta": self.meta,
        }
        if self.passthrough:  # sin la clave, la huella de los parámetros de antes no cambia
            out["passthrough"] = self.passthrough
        return out

    @property
    def sha256(self) -> str:
        text = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _lookup(self, table: dict, keys: list[str]):
        return next((table[k] for k in keys if k in table), None)

    def curve_for(
        self, strategy: str, channel: str | None, media: str | None = None
    ) -> dict | None:
        channel = channel or "*"
        base = _base(strategy)
        keys = [f"{strategy}|{channel}|{media}", f"{base}|{channel}|{media}"] if media else []
        keys += [f"{strategy}|{channel}", f"{base}|{channel}", f"{strategy}|*", f"{base}|*"]
        return self._lookup(self.curves, [*keys, f"*|{channel}", "*|*"])

    def threshold_for(self, strategy: str) -> float | None:
        return self._lookup(self.thresholds, [strategy, _base(strategy), "*"])

    def quantile_for(
        self, kind: str, confidence: float, strategy: str | None = None
    ) -> float | None:
        band = conformal.band_of(confidence)
        keys = [f"{kind}|{band}", f"{kind}|*"]
        if strategy:  # cuantil de la propia estrategia si se ajustó; si no, el de todas
            base = _base(strategy)
            keys = [f"{strategy}|{kind}|{band}", f"{base}|{kind}|{band}", *keys]
        return self._lookup(self.quantiles, keys)

    def calibrated(
        self, strategy: str, channel: str | None, raw: float, media: str | None = None
    ) -> float:
        curve = None if strategy in self.passthrough else self.curve_for(strategy, channel, media)
        value = raw if curve is None else apply_curve(curve, raw)
        return round(min(1.0, max(0.0, value)), 4)

    def apply(
        self, candidates: list[Candidate], strategy: str, scanned: frozenset[str] = frozenset()
    ) -> tuple[list[Candidate], dict]:
        """Candidatos calibrados y un resumen para el evento de la etapa.

        `scanned`: ids de los documentos PDF sin capa de texto.
        """
        threshold = self.threshold_for(strategy)
        out, intervals, abstained = [], 0, 0
        for c in candidates:
            raw = c.source.confidence
            channel = c.channel or c.source.channel
            media = "scan" if c.source.document_id in scanned else "vector"
            confidence = self.calibrated(strategy, channel, raw, media)
            update: dict = {
                "source": c.source.model_copy(
                    update={"confidence": confidence, "confidence_raw": raw}
                )
            }
            kind = conformal.kind_of(c.value, c.unit)
            q = None if kind is None else self.quantile_for(kind, confidence, strategy)
            vague = False
            if q is not None and isinstance(c.value, float | int):
                if conformal.informative(kind, q):
                    width = conformal.half_width(kind, float(c.value), q)
                    update["interval"] = Interval(
                        low=float(c.value) - width, high=float(c.value) + width, level=self.level
                    )
                    intervals += 1
                else:
                    vague = True
            note = None
            if threshold is not None and confidence < threshold:
                note = (
                    f"Abstención: confianza calibrada {_es(confidence)} por debajo del umbral "
                    f"{_es(threshold)}; confírmelo en la revisión."
                )
            elif vague:
                note = (
                    f"Abstención: con confianza {_es(confidence)}, más del "
                    f"{(1 - self.level) * 100:.0f} % de las lecturas parecidas fallan por "
                    "mucho y no hay intervalo útil; confírmelo en la revisión."
                )
            if note is not None:
                update["state"] = "abstained"
                update["explanation"] = f"{c.explanation} {note}" if c.explanation else note
                abstained += 1
            out.append(c.model_copy(update=update))
        return out, {"fields": len(out), "intervals": intervals, "abstained": abstained}


def load_calibration(path: Path | None = None) -> Calibration | None:
    """Parámetros de calibración, o `None` si no hay (la etapa queda omitida)."""
    path = path or calibration_path()
    if path is None or not path.is_file():
        return None
    return Calibration.from_dict(json.loads(path.read_text(encoding="utf-8")))


__all__ = ["Calibration", "calibration_path", "load_calibration"]
