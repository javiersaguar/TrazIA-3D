# Alcance frente al reto completo

Enunciado: PDF de 17 páginas compartido por Javier, consultado el 26 de octubre de 2026.
Referencia pública: [GA2MODEL](https://indesiahack.org/tecnicas-reunidas-2026).
Nombre del producto: **TrazIA-3D**; GA2MODEL es el nombre del reto.

## Criterios de evaluación

| Peso publicado (p. 15) | Base actual | Próxima evidencia necesaria |
| --- | --- | --- |
| 35% fidelidad geométrica | Familia vertical, fondos, faldón, boquillas y visor IFC | Error de dimensiones/posiciones frente a IFC oficial |
| 25% atributos | Valores, unidades, evidencia, confianza y Excel | Acierto y calibración en documentos reales |
| 20% actualización | Delta por campo y GUID estables; conserva A/B | Precisión/recobrado con pares reales |
| 10% arquitectura y escala | Módulos separados, CLI, esquema y pruebas | Coste/latencia por equipo; colas y persistencia |
| 10% innovación | Evidencia visual y aprobación ligada a huella | Validar utilidad con un usuario de ingeniería |

No hay aún métricas de precisión ni resultados sobre el dataset de Técnicas Reunidas.

## Requisitos concretos

Las pp. 8–11 piden GA y HDM, dimensiones externas, tag, soporte, ≥3 boquillas con posición
y orientación; IFC cargable con carcasa, tapas, boquillas y soporte; JSON y visor con
checkpoint humano. El flujo automático debe generar DRAFT (p. 9).

El visor se considera parte del MVP: aunque la p. 10 lo recomienda, la p. 11 lo marca
obligatorio. La actualización se incluye porque figura en las cuatro capacidades del MVP
y pesa un 20% en la evaluación, aunque las pp. 11–12 la presentan como diferencial/bonus.

## Decisiones iniciales

- Familia paramétrica de estáticos verticales para acotar la primera demo. No inferir que
  todo el dataset tiene esta geometría; la p. 13 también incluye bombas, compresores y tanques.
- Python + IfcOpenShell para extracción/validación/geometría; Streamlit + Plotly como espacio
  local de revisión que puede sustituirse por otro frontend sin cambiar el contrato.
- IFC4, entre las versiones admitidas por el reto. Fondos teselados con geometría cerrada.
- Valor/unidad/fuente por campo, documento con SHA-256 y revisiones documentales independientes.
- La entrada de un futuro extractor IA es candidata hasta la validación y revisión humana.
- No se selecciona aún proveedor IA: necesita muestras para valorar calidad, coste y datos.

## Siguiente hito con el dataset oficial

1. Elegir un recipiente con GA rev1/rev2, HDM, VESOR e IFC de referencia.
2. Construir una referencia manual de dimensiones, boquillas, atributos y evidencias.
3. Conectar un extractor multimodal mediante `Extractor`, incluyendo OCR para escaneos.
4. Reconciliar vistas y tablas, preservar desconocidos y mostrar conflictos; no inventar valores.
5. Medir error absoluto en mm/grados, acierto por atributo, precisión/recobrado de cambios,
   calibración de confianza y porcentaje de campos con evidencia válida.
6. Revisar la familia geométrica frente al IFC oficial; añadir soportes/orientaciones que falten.
7. Preparar un caso independiente de evaluación para evitar ajustar solo a un plano.

## Trabajo posterior

Persistencia de versiones y originales, recortes de evidencia mejorados, unidades de atributos
normalizadas, emparejamiento de IDs entre extractores, orientación/inclinación de boquillas,
otras familias, exportación BCF, colas y costes. La base actual no afirma resolverlos.
