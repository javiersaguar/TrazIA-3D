"""Hoja de contacto de stills QA: python -I scripts/sheet.py salida.png f1.png f2.png ..."""
import sys, cv2, numpy as np
out, files = sys.argv[1], sys.argv[2:]
tiles = []
for f in files:
    im = cv2.imread(f)
    im = cv2.resize(im, (960, 540))
    cv2.putText(im, f.split('/')[-1], (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    tiles.append(im)
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
cv2.imwrite(out, np.vstack(rows))
