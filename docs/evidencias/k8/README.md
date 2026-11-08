# K8 · piezas, familias y GA nuevos

08/11/2026. Solo fixtures sintéticos públicos. Ejecución en CPU, sin proveedores de visión,
datos privados ni evaluación humana. Los originales permanecen intactos.

## Resultado

- Altas/bajas de boquillas, plataformas y escaleras mediante propuestas reversibles.
- Dimensiones específicas de vertical, horizontal, columna y tanque; envolventes de todas
  las familias LOD 1. Bombas/compresores no incorporan interiores mecánicos ficticios.
- Tres proyecciones ortográficas de la malla IFC, PDF vectorial y SVG A3, cotas exteriores,
  escala común, cajetín DRAFT y manifiesto con GUID completos y huellas. La API permite
  descargar exactamente el IFC que originó el plano.

Los PDF, SVG, PNG renderizados y manifiestos de esta carpeta se generan con:

```powershell
uv run --extra dev --extra api python scripts/verify_k8_drawings.py
```

El script utiliza el fixture de familias de `tests/test_plataforma_families.py` y el V-101
de `examples/`. Las huellas IFC cambian al regenerar su cabecera temporal. El manifiesto
acompañante corresponde a los bytes de la ejecución registrada, no a una futura regeneración.

## Medidas de esta ejecución

Python 3.12 en contenedor Linux CPU sobre el portátil Windows. Una ejecución por familia;
no son percentiles, una prueba de carga ni resultados sobre planos de TR. Tiempo del GA separado
de la construcción IFC; no incluye EXPRESS, cola, descarga ni revisión humana.

| Fixture | IFC, s | GA, s | Escala |
| --- | ---: | ---: | ---: |
| Vertical | 0,1984 | 0,6456 | 1:100 |
| Horizontal | 0,0315 | 0,5478 | 1:100 |
| Columna | 0,0151 | 0,1373 | 1:100 |
| Tanque | 0,0105 | 0,0957 | 1:100 |
| Bomba, envolvente | 0,0106 | 0,0108 | 1:50 |
| Compresor, envolvente | 0,0135 | 0,0136 | 1:50 |
| Genérico, envolvente | 0,0092 | 0,0092 | 1:50 |

Valores originales en [mediciones.json](mediciones.json). Se inspeccionaron los PNG renderizados
para comprobar legibilidad, márgenes, cotas y vistas. Los tests contrastan A3 físico,
escala admitida, geometría efectiva, SHA y persistencia de GUID, además de la publicación API.

## Límites y decisión de alcance

- Las cotas son extensiones de la **malla completa**, incluidas conexiones, no el diámetro
  interior de la virola. La teselación introduce aproximación geométrica.
- No se resuelven líneas ocultas, tolerancias, soldaduras, esfuerzos ni requisitos de fabricación.
  Es un GA derivado DRAFT para revisar; no sustituye un plano aprobado.
- Plataformas/escaleras requieren parámetros explícitos y LOD 3. No se certifica su soporte
  resistente ni se ajusta su posición automáticamente.
- Conexiones explícitas: solo las superficies de virola comprobadas por el catálogo; una posición
  incompatible se rechaza. No se rediseñan automáticamente las conexiones al cambiar la virola.
- Se evaluaron órdenes de varios equipos, permisos por rol y aprobación por disciplina:
  se mantienen **fuera de esta entrega**. La transacción y el ETag actuales protegen una revisión;
  una orden multiequipo necesita un agregado transaccional y recuperación parcial explícitos.
  El actor declarado no autentica una identidad. RBAC requiere autenticación y una política de
  autorización en servidor antes de poder presentarlo como control de permisos.
- Cancelar/expirar impide publicar. La tarea CPU en un hilo puede terminar su cálculo en segundo
  plano; no se promete terminación inmediata del hilo nativo de IfcOpenShell.
- No se cierran el ensayo del modelo local, las sesiones humanas ni el contraste con la referencia TR.
