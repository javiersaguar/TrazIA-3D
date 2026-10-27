# Estudio comparativo de estrategias · resultados

Generado 2026-10-27T11:53:12+00:00 · generador v2 · semilla del bootstrap 2026.

> **Datos sintéticos.** Proveedores ficticios con verdad conocida. No es precisión sobre planos reales de Técnicas Reunidas.

Conjuntos: S-dev (semilla 2026, 24 equipos)

## Variantes medidas (S-dev)

| Variante | Puntuación | IC 95 % | Geometría | Atributos | ECE | F1 cambios | Alucinación | Cita | s/rev | €/equipo | Elegible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `b_reglas` | 0,389 | [0,327; 0,449] | 5,6 % | 69,4 % | 0,175 | 13,2 % | 0,0 % | 100,0 % | 0,02 | 0,00 | sí |
| `b_reglas-hdm` | 0,280 | [0,235; 0,324] | 5,6 % | 15,3 % | 0,122 | 13,2 % | 0,0 % | 100,0 % | 0,01 | 0,00 | sí |

## Por conjunto

| Variante | Conjunto | Puntuación | Geometría | Geometría sin penalizar | Atributos | Modelos IFC | Envenenamiento |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `b_reglas` | S-dev | 0,389 | 5,6 % | 7,7 % | 69,4 % | 5,6 % | — |
| `b_reglas-hdm` | S-dev | 0,280 | 5,6 % | 7,7 % | 15,3 % | 5,6 % | — |

## Por proveedor

| Variante | Grupo | Puntuación | Geometría | Atributos |
| --- | --- | --- | --- | --- |
| `b_reglas` | atlas | 0,634 | 33,3 % | 100,0 % |
| `b_reglas` | iberica | 0,400 | 0,0 % | 100,0 % |
| `b_reglas` | gulf | 0,213 | 0,0 % | 8,3 % |
| `b_reglas` | prairie | 0,390 | 0,0 % | 100,0 % |
| `b_reglas` | nordic | 0,399 | 0,0 % | 100,0 % |
| `b_reglas` | levante | 0,219 | 0,0 % | 8,3 % |
| `b_reglas-hdm` | atlas | 0,491 | 33,3 % | 33,3 % |
| `b_reglas-hdm` | iberica | 0,219 | 0,0 % | 8,3 % |
| `b_reglas-hdm` | gulf | 0,213 | 0,0 % | 8,3 % |
| `b_reglas-hdm` | prairie | 0,218 | 0,0 % | 8,3 % |
| `b_reglas-hdm` | nordic | 0,254 | 0,0 % | 25,0 % |
| `b_reglas-hdm` | levante | 0,219 | 0,0 % | 8,3 % |

## Por degradación

| Variante | Grupo | Puntuación | Geometría | Atributos |
| --- | --- | --- | --- | --- |
| `b_reglas` | vectorial | 0,490 | 16,7 % | 75,0 % |
| `b_reglas` | escaneado_limpio | 0,325 | 0,0 % | 66,7 % |
| `b_reglas` | escaneado_pobre | 0,325 | 0,0 % | 66,7 % |
| `b_reglas-hdm` | vectorial | 0,429 | 16,7 % | 45,8 % |
| `b_reglas-hdm` | escaneado_limpio | 0,200 | 0,0 % | 0,0 % |
| `b_reglas-hdm` | escaneado_pobre | 0,200 | 0,0 % | 0,0 % |

## Ablaciones

| Ablación | De | Δ puntuación | IC 95 % |
| --- | --- | --- | --- |
| `b_reglas-hdm` | `b_reglas` | -0,110 | [-0,139; -0,077] |

## Comparaciones pareadas (McNemar exacto, campo a campo)

| A | B | Solo A acierta | Solo B acierta | Campos | p |
| --- | --- | --- | --- | --- | --- |
| `b_reglas` | `b_reglas-hdm` | 312 | 0 | 4584 | 2.4e-94 |

## Frontera de Pareto (coste, tiempo, puntuación)

`b_reglas`, `b_reglas-hdm`

## Recomendación

- Vectorial: `b_reglas`
- Escaneado: `b_reglas`
- Elegida por mayor Puntuación GA2MODEL entre las variantes que cumplen alucinación < 1 % y cita = 100 %, sobre S-dev y S-reservado (sintéticos). vectorial: b_reglas (puntuación 0,490, geometría 16,7 %, atributos 75,0 %); escaneado: b_reglas (puntuación 0,325, geometría 0,0 %, atributos 66,7 %).

## Sin medir

- Nada.
