"""Las estrategias de lectura de la pág. 13 del reto, detrás de una misma interfaz."""

from .b_reglas import ReglasStrategy
from .base import Cost, StageEvent, Strategy, StrategyContext, StrategyOutput

STRATEGIES: dict[str, type] = {"b_reglas": ReglasStrategy}


def get_strategy(name: str) -> Strategy:
    try:
        return STRATEGIES[name]()
    except KeyError:
        raise ValueError(
            f"Estrategia desconocida: {name}. Disponibles: {', '.join(sorted(STRATEGIES))}"
        ) from None


__all__ = [
    "STRATEGIES",
    "Cost",
    "StageEvent",
    "Strategy",
    "StrategyContext",
    "StrategyOutput",
    "get_strategy",
]
