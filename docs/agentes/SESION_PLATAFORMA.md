# Sesión Plataforma · 30/10/2026

Rama `feat/plataforma`, worktree `../TrazIA-3D-plataforma`, desde `feat/web-3d`
con el frontend integrado y la tarea 2.6 cerrada. Sin push ni PR.

Se ha leído [SESION_LECTURA.md](SESION_LECTURA.md). No se editan las carpetas,
pruebas ni documentos reservados a Lectura; tampoco se usa la GPU para esta sesión.

## Trabajo reservado en esta sesión

- H.1/H.3: lanzar el estudio mediante la cola existente, con idempotencia, SSE,
  cancelación, timeout y resultados por trabajo. Adaptador al arnés actual, sin editar `bench/`.
- 4.2: activar la caché de visión con `TRAZIA_OFFLINE=1` en los puntos de entrada de
  Plataforma y añadir caché del copiloto con invalidación por datos/modelo/código.
- 3.8, parte independiente: exportar correcciones humanas trazadas para la futura
  recalibración de Lectura. No se afirma recalibración sin su interfaz pública.

El aviso de solape de 2.6 ya está resuelto en esta rama: `c4a8ff2` contiene el detalle IFC;
los visores usan esos productos y el detalle es optativo en `build_ifc`.

## Interfaz con Lectura

El arnés actual expone `run_study(data, sets, variant_ids, ...)`; Plataforma lo ejecuta
en un subproceso aislado. Cuando se publique la firma de `ejecutar(config, on_event)`,
se podrá sustituir el adaptador. Los informes nuevos se guardan por trabajo en el
almacén SHA-256, sin sobrescribir `generated/estudio/` del otro agente.

El informe final registra las verificaciones y qué puntos del roadmap siguen parciales.

## Cierre

Las tres tareas reservadas están implementadas dentro de su alcance independiente.
240 pruebas Python pasan; el estudio real también funciona con Redis/arq/Postgres.
[Verificación y límites](../BACKEND_2026-10-30.md). 3.7/H.7 y 3.8 siguen parciales.
