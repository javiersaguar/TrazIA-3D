"""Un reajuste de B no cambia la confianza ni los intervalos de C o D."""

from . import Calibration


def for_strategy(calibration: Calibration | None, strategy: str) -> Calibration | None:
    while calibration is not None:
        scope = calibration.meta.get("feedback_strategies")
        if not scope or strategy in scope or strategy.split("-")[0] in scope:
            return calibration
        fallback = calibration.meta.get("feedback_fallback")
        calibration = Calibration.from_dict(fallback) if fallback else None
    return None
