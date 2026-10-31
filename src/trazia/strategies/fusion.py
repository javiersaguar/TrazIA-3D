"""Fusión aprendida de D (tarea 3.4).

La fusión heurística de D puntúa cada lectura candidata de un campo con reglas fijas: lecturas
iguales de canales distintos se refuerzan, la geometría confirma o penaliza y las restricciones de
ingeniería suben o bajan. Aquí esas mismas señales entran en una regresión logística que da la
probabilidad de que la lectura sea correcta; gana la más probable y esa probabilidad es su
confianza.

Opciones de un campo: cada grupo de lecturas iguales y, si hay medida del dibujo que ningún grupo
confirma, la propia medida. Así el modelo aprende cuándo fiarse del dibujo frente a lo leído, en
lugar de la regla fija «el dibujo vectorial gana si todas las lecturas lo contradicen».

Si un campo tiene lecturas de un canal que no aparece en S-dev (p. ej. «texto», del extractor de
etiquetas de los planos antiguos), ese campo se fusiona con la heurística: el modelo no sabe nada
de ese canal.

Desde el 31/10 es la fusión de D por defecto. Los coeficientes se ajustan con
`uv run python -m bench.fusion` sobre S-dev (en `generated/fusion/`) y, con `--publicar`, se copian
a `fusion_model.json`, junto a este módulo, que se versiona en Git: un clon limpio usa el mismo
modelo. Es JSON, sin pickle, y solo contiene coeficientes. Otra ruta: `TRAZIA_FUSION`; `off`
vuelve a la heurística. La inferencia es una suma ponderada: el producto no necesita scikit-learn.
"""

import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

FORMAT = 1
PACKAGED_PATH = Path(__file__).with_name("fusion_model.json")
DEFAULT_PATH = str(PACKAGED_PATH)

SOURCE_CHANNELS = (
    "texto",
    "tabla",
    "cota",
    "cajetin",
    "hoja_datos",
    "ocr",
    "detector",
    "rag",
    "memoria_revision",
    "vision",
    "geometria",
)
MAIN = ("diameter", "height", "skirt_height", "head_depth")
FEATURES = (
    *(f"ch_{c}" for c in SOURCE_CHANNELS),
    "n_channels",
    "n_evidence",
    "base",
    "share",
    "rivals",
    "geo_confirms",
    "geo_contradicts",
    "geo_none",
    "geo_vector",
    "rule_up",
    "rule_down",
    "measure_only",
    "measure_conf",
    "measure_vector",
    "measure_main",
    "k_main",
    "k_nozzle_pos",
    "k_nozzle_dn",
    "k_attr",
    "k_tag",
)


def field_kind(path: str) -> str:
    if path == "tag":
        return "tag"
    if path in MAIN:
        return "main"
    if path.startswith("attributes."):
        return "attr"
    if path.startswith("nozzles.") and path.endswith(".diameter"):
        return "nozzle_dn"
    if path.startswith("nozzles."):
        return "nozzle_pos"
    return "other"


def _kind_features(path: str) -> dict[str, float]:
    kind = field_kind(path)
    return {f"k_{k}": float(kind == k) for k in ("main", "nozzle_pos", "nozzle_dn", "attr", "tag")}


def cluster_features(
    path: str,
    *,
    per_channel: dict[str, float],
    n_evidence: int,
    base: float,
    share: float,
    n_options: int,
    geo: int | None,
    geo_vector: bool,
    rule: int,
) -> dict[str, float]:
    """Señales de un grupo de lecturas iguales.

    `geo`: 1 si la medida del dibujo lo confirma, -1 si lo contradice, 0 si queda entre medias y
    None si no hay medida. `rule`: +1, -1 o 0 según las restricciones de ingeniería.
    """
    out = {f"ch_{c}": float(per_channel.get(c, 0.0)) for c in SOURCE_CHANNELS}
    out |= {
        "n_channels": len(per_channel) / 3,
        "n_evidence": min(n_evidence, 6) / 3,
        "base": base,
        "share": share,
        "rivals": min(n_options - 1, 3) / 3,
        "geo_confirms": float(geo == 1),
        "geo_contradicts": float(geo == -1),
        "geo_none": float(geo is None),
        "geo_vector": float(geo_vector),
        "rule_up": float(rule > 0),
        "rule_down": float(rule < 0),
        "measure_only": 0.0,
        "measure_conf": 0.0,
        "measure_vector": 0.0,
        "measure_main": 0.0,
    }
    return out | _kind_features(path)


def measure_features(
    path: str, *, confidence: float, vector: bool, n_options: int, contradicted: int
) -> dict[str, float]:
    """Señales de la medida del dibujo como opción propia (sin lectura que la confirme)."""
    out = {f"ch_{c}": 0.0 for c in SOURCE_CHANNELS}
    kinds = _kind_features(path)
    out |= {
        "n_channels": 0.0,
        "n_evidence": 0.0,
        "base": 0.0,
        "share": 0.0,
        "rivals": min(n_options - 1, 3) / 3,
        "geo_confirms": 0.0,
        "geo_contradicts": float(contradicted > 0),
        "geo_none": 0.0,
        "geo_vector": float(vector),
        "rule_up": 0.0,
        "rule_down": 0.0,
        "measure_only": 1.0,
        "measure_conf": confidence,
        "measure_vector": float(vector),
        "measure_main": kinds["k_main"],
    }
    return out | kinds


@dataclass
class FusionModel:
    features: list[str]
    coef: list[float]
    intercept: float
    fitted_on: str = ""
    meta: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "FusionModel":
        if data.get("format") != FORMAT:
            raise ValueError(f"Formato de fusión no admitido: {data.get('format')}")
        if len(data["features"]) != len(data["coef"]):
            raise ValueError("Fusión: número de coeficientes distinto del de señales")
        return cls(
            features=list(data["features"]),
            coef=[float(c) for c in data["coef"]],
            intercept=float(data["intercept"]),
            fitted_on=data.get("fitted_on", ""),
            meta=data.get("meta", {}),
        )

    def to_dict(self) -> dict:
        return {
            "format": FORMAT,
            "features": self.features,
            "coef": self.coef,
            "intercept": self.intercept,
            "fitted_on": self.fitted_on,
            "meta": self.meta,
        }

    @property
    def sha256(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def covers(self, channels) -> bool:
        """Si el modelo vio todos estos canales al ajustarse. Un canal que no vio no tiene peso:
        sus lecturas valdrían como ausencia de prueba. Ese campo se fusiona con la heurística."""
        seen = self.meta.get("channels_seen")
        return seen is None or all(c in seen for c in channels)

    def prob(self, features: dict[str, float]) -> float:
        z = self.intercept + sum(w * features.get(n, 0.0) for n, w in zip(self.features, self.coef))
        z = max(-30.0, min(30.0, z))
        return 1 / (1 + math.exp(-z))


def fusion_path() -> Path | None:
    value = os.environ.get("TRAZIA_FUSION", DEFAULT_PATH).strip()
    if value.lower() in ("", "0", "off", "no"):
        return None
    return Path(value)


def load_fusion(path: Path | None = None) -> FusionModel | None:
    """Modelo ajustado, o None si no hay. Un fichero ilegible es un error, no un «no hay»."""
    path = path or fusion_path()
    if path is None or not path.exists():
        return None
    return FusionModel.from_dict(json.loads(path.read_text(encoding="utf-8")))
