# Entrada de la landing · 08/11/2026

Comparación local contra `ee82f1f`, con compilaciones de producción y datos sintéticos.
Se conservan la composición, los logos, los colores y la formación del logo antes del vuelo.

## Cambios

- Formación de los dos logos mediante CSS, sin un controlador JavaScript por trazo.
- Vuelo con dos transformaciones nativas del navegador: símbolo y nombre. Sus posiciones
  se miden una vez; se conserva el mismo nodo hasta llegar a la cabecera.
- Fases explícitas: formación, vuelo y contenido. El dibujo del hero y las escenas PDF/IFC
  empiezan después del vuelo; antes algunas escenas se montaban debajo de la intro.
- El diálogo de demostración se descarga al pulsar su botón, con retorno del foco al cerrar.
- Escape/clic permiten saltar la formación. Redimensionar durante el vuelo lo finaliza;
  movimiento reducido muestra directamente el contenido.

## Medición

Tres contextos nuevos de Chrome por versión, 1600 × 940, CPU limitada a 4× y WebGL software
SwiftShader. Ventana de 800 ms desde el inicio del vuelo. Antes se detecta por la retirada
del nodo de formación; después mediante la fase explícita. Los datos completos están en
`antes.json`, `despues.json` y `peso.json`.

| Medida | Antes | Después |
| --- | ---: | ---: |
| Mayor separación entre callbacks rAF, pasada 1 | 337,5 ms | 116,6 ms |
| Mayor separación entre callbacks rAF, pasada 2 | 120,9 ms | 41,6 ms |
| Mayor separación entre callbacks rAF, pasada 3 | 100,0 ms | 41,6 ms |
| Mediana de esas separaciones máximas | 120,9 ms | 41,6 ms |
| Solapamiento con tareas JS largas durante el vuelo, pasadas 1/2/3 | 239,7 / 397,5 / 374,0 ms | 0 / 0 / 0 ms |
| Montaje de la primera escena canvas | Antes del vuelo en 3/3 | Después de finalizar en 3/3 |
| Suma gzip de scripts iniciales presentes en HTML | 315.625 bytes | 307.793 bytes |
| Número de esos scripts | 19 | 18 |
| HTML gzip | 17.335 bytes | 17.539 bytes |

`blockingMs` en los JSON suma la parte de cada tarea larga que cae dentro de la ventana;
no es la métrica estándar TBT. rAF mide disponibilidad del hilo principal, no los FPS del
compositor. Son tres muestras locales, no una acreditación de rendimiento en Vercel ni
en la RTX. El primer recorrido posterior aún registra una separación de 116,6 ms; no se
afirma que desaparezca toda irregularidad. La medida de peso excluye CSS, imports diferidos
y sobrecarga de red; el presupuesto global de 250 KB gzip continúa pendiente.

Para repetir con ambas versiones sirviéndose en puertos distintos, desde `web/`:

```powershell
node scripts/profile-intro.mjs http://127.0.0.1:3120/ ../generated/intro-antes.json
node scripts/profile-intro.mjs http://127.0.0.1:3121/ ../generated/intro-despues.json
node scripts/measure-landing-weight.mjs ../generated/peso-landing.json http://127.0.0.1:3120/ http://127.0.0.1:3121/
```

## Validación

Typecheck, lint, build y 58 pruebas unitarias correctos. Lint conserva el aviso previo de
React Compiler/TanStack Table en Proyecto. Cinco recorridos Playwright de producción
correctos: entrada completa, salto/redimensionado, movimiento reducido, apertura/cierre
del diálogo diferido y regresión de la sección de holograma.

Capturas inspeccionadas: `logos-formados.png`, `vuelo-intermedio.png` y `entrada-final.png`.
Las dos primeras fijan las animaciones para inspección; no son mediciones de rendimiento.
Sin dependencias nuevas, cambios de API, datos privados ni ejecución de modelos.
