"""Las estrategias de lectura de la pág. 13 del reto, detrás de una misma interfaz."""

from collections.abc import Callable

from .a_vision import VisionGeometryStrategy
from .b_reglas import ReglasStrategy
from .base import Cost, StageEvent, Strategy, StrategyContext, StrategyOutput
from .c_rag import RagStrategy
from .d_hibrido import HybridStrategy

STRATEGIES: dict[str, Callable[[], Strategy]] = {
    "b_reglas": ReglasStrategy,
    "b_reglas+ocr": lambda: ReglasStrategy(ocr=True, name="b_reglas+ocr"),
    "a_geometria": lambda: VisionGeometryStrategy(reader="texto", name="a_geometria"),
    "a_vision": lambda: VisionGeometryStrategy(reader="vision", name="a_vision"),
    "c_rag": RagStrategy,
    "d_hibrido": HybridStrategy,
}

# Ablaciones del estudio: «<estrategia>-<canal quitado>». No se ofrecen en la API.
ABLATIONS: dict[str, Callable[[], Strategy]] = {
    "b_reglas-tablas": lambda: ReglasStrategy(drawing=False, name="b_reglas-tablas"),
    "b_reglas-hdm": lambda: ReglasStrategy(hdm=False, name="b_reglas-hdm"),
    **{
        f"d_hibrido-{channel}": (
            lambda channel=channel: HybridStrategy(without={channel}, name=f"d_hibrido-{channel}")
        )
        for channel in ("geometria", "memoria", "rag", "vision", "detector")
    },
    # Variantes del estudio que no quitan un canal: D con fusión aprendida (3.4) y A con el
    # detector propio como lector (2.4).
    "d_hibrido+fusion": lambda: HybridStrategy(fusion="aprendida", name="d_hibrido+fusion"),
    "a_detector": lambda: VisionGeometryStrategy(reader="detector", name="a_detector"),
}


def get_strategy(name: str) -> Strategy:
    factory = STRATEGIES.get(name) or ABLATIONS.get(name)
    if factory is None:
        raise ValueError(
            f"Estrategia desconocida: {name}. Disponibles: {', '.join(sorted(STRATEGIES))}"
        )
    return factory()


__all__ = [
    "ABLATIONS",
    "STRATEGIES",
    "Cost",
    "StageEvent",
    "Strategy",
    "StrategyContext",
    "StrategyOutput",
    "get_strategy",
]
