"""Tapa el subtítulo de la barra lateral («Técnicas Reunidas …») en las capturas 2x.

El vídeo no debe sugerir que TR usa el producto. Se rellena la zona con el color de la barra lateral.
Idempotente: guarda el original una vez en public/captures/_orig/ y siempre parte de él.
Uso: python -I scripts/redact.py
"""
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent / 'public' / 'captures'
ORIG = ROOT / '_orig'
BOX = (112, 62, 372, 100)  # subtítulo bajo «TrazIA 3D», coordenadas a 2x

ORIG.mkdir(exist_ok=True)
for name in ('documentos', 'revision', 'cambios'):
    src = ROOT / f'{name}.png'
    keep = ORIG / f'{name}.png'
    if not keep.exists():
        shutil.copy2(src, keep)
    im = Image.open(keep).convert('RGB')
    bg = im.getpixel((BOX[2] + 4, BOX[1] + 2))
    ImageDraw.Draw(im).rectangle(BOX, fill=bg)
    im.save(src)
    print(name, 'fill', bg)
