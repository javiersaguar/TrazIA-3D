"""Las estrategias de lectura de la pág. 13 del reto, detrás de una misma interfaz."""

from collections.abc import Callable

from .b_reglas import ReglasStrategy
from .base import Cost, StageEvent, Strategy, StrategyContext, StrategyOutput

STRATEGIES: dict[str, Callable[[], Strategy]] = {"b_reglas": ReglasStrategy}

# Ablaciones del estudio: «<estrategia>-<canal quitado>». No se ofrecen en la API.
ABLATIONS: dict[str, Callable[[], Strategy]] = {
    "b_reglas-tablas": lambda: ReglasStrategy(drawing=False, name="b_reglas-tablas"),
    "b_reglas-hdm": lambda: ReglasStrategy(hdm=False, name="b_reglas-hdm"),
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
