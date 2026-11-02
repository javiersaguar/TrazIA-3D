# D.4 · Auditoría automática de IFC sintéticos · 02/11

**48/48 combinaciones válidas**, 266.972 s en la ejecución archivada. Sin GPU, visor
externo ni referencia TR. Son comprobaciones internas contra parámetros sintéticos, no precisión
sobre planos ni dimensionado mecánico. [Informe completo](matrix.json).

Ocho casos: vertical, horizontal, columna, tanque cónico, tanque abovedado, bomba, compresor y
reserva genérica. Se cruzan IFC4/IFC4X3/IFC2X3 con detalle visual activado/desactivado. Cada
combinación genera también una revisión B para verificar estabilidad de GUID: 96 exportaciones
comprobadas en total. En familias sin detalle adicional, ambos modos conservan la misma geometría.

La auditoría reabre STEP antes de comprobar reglas EXPRESS, unidad de longitud en metros,
GUID únicos, propiedades trazadas/huella de datos y valores técnicos, FieldsJSON frente al
contrato, envolventes analíticas por componente y posición/dirección de cada puerto. Tolerancia
geométrica 0,002 m y de colocación de puertos 1e-6 m. Los datos de origen se mantienen intactos.

Las pruebas negativas alteran unidad, estado DRAFT, FieldsJSON, presión, posición y dirección:
un IFC que abre y cumple su esquema todavía puede fallar estas comprobaciones. Los resultados
no prueban ausencia de colisiones, resistencia mecánica ni todas las geometrías posibles.

```powershell
uv run python scripts/audit_ifc_matrix.py --output generated/ifc-audit
```

Los 48 archivos A quedan en la carpeta generated elegida; los B se auditan sin guardarlos. Sus
huellas y componentes constan en el JSON. Las definiciones públicas están en
`scripts/ifc_audit_fixtures.py`; el auditor está en `trazia.families.audit` y puede contrastar un
DRAFT con su Revision. Las marcas y datos derivados se conservan explícitos.

La apertura visual previa en tres visores permanece documentada en [01/11](../01nov/README.md).
El contraste de cotas y propiedades **dentro de BIMvision** sigue pendiente de lectura manual;
C.4/D.5 siguen pendientes del IFC de TR. Esta matriz cierra la ampliación automática de esta sesión,
no esas validaciones externas.
