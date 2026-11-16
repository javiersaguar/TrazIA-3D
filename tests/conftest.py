"""Hace importables los paquetes de la raíz (bench/, synthetic/) en las pruebas."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# La precarga (runtime.warm_up) carga OCR y módulos pesados al arrancar la API: en las pruebas no.
os.environ.setdefault("TRAZIA_WARMUP", "0")
