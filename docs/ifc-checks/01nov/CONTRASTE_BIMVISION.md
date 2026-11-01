# Contraste del recipiente V-101 en BIMvision

Estado: **pendiente de lecturas en BIMvision**. La apertura y visualización del mismo archivo ya
constan en la captura aportada por Javier; el controlador detecta el proceso pero no devuelve
ninguna ventana accesible. No se han realizado clics ni mediciones en ese visor durante esta
comprobación. Estos valores proceden exclusivamente del archivo IFC, leído en CPU con IfcOpenShell.

Archivo: [V-101_B_DRAFT.ifc](V-101_B_DRAFT.ifc). SHA-256 `9ca68e1230d7c4ca62668786ed95308d8c20c229151b2d2945930422c451472c`.
[Referencia completa por componente](referencia-contraste.json).

## Unidades y cotas de referencia

| Magnitud | Referencia del IFC | Lectura en BIMvision |
| --- | --- | --- |
| Unidad de longitud del IFC | METRE, sin prefijo | Pendiente |
| Unidad de entrada declarada | mm | Pendiente |
| Diámetro de la virola | 2 m = 2.000 mm | Pendiente |
| Longitud de la virola, entre tangencias | 6,5 m = 6.500 mm | Pendiente |
| Altura del faldón | 1,35 m = 1.350 mm | Pendiente |
| Profundidad de cada fondo | 0,5 m = 500 mm | Pendiente |

Las cotas se obtienen de la envolvente de cada componente con coordenadas mundiales; la virola
abarca Z=1,35…7,85 m. Su longitud no es la altura total del recipiente. La teselación y los
puntos elegidos pueden afectar una medición manual. Indicar la unidad que muestre el visor:
2 m y 2.000 mm son equivalentes, sin exigir cambiar sus ajustes de visualización.

## Propiedades de referencia

Seleccionar el cuerpo central, componente `shell`, nombre V-101; no el proyecto completo.

| Propiedad / conjunto | Valor del archivo | Lectura en BIMvision |
| --- | --- | --- |
| IfcEntity | IfcTank | Pendiente |
| GlobalId | `2LWeWJOpTHLgKbI2kTXlHK` | Pendiente |
| TrazIA_Identity.ComponentId | shell | Pendiente |
| TrazIA_Identity.EquipmentId | vessel-001 | Pendiente |
| Pset_TankTypeCommon.Reference | V-101 | Pendiente |
| TrazIA_Provenance.Revision | B | Pendiente |
| TrazIA_Provenance.Dataset | synthetic | Pendiente |
| TrazIA_Provenance.Draft | True | Pendiente |
| TrazIA_Provenance.LOD | 2 | Pendiente |
| TrazIA_ReferenceFrame.IFCLengthUnit | m | Pendiente |
| TrazIA_Technical.design_pressure | 16.0 bar | Pendiente |
| TrazIA_Technical.design_temperature | 180.0 C | Pendiente |
| TrazIA_Technical.material | SA-516-70 1 | Pendiente |
| TrazIA_Technical.operating_weight | 12800.0 kg | Pendiente |

El sufijo `1` del material es la unidad adimensional serializada por el exportador; se conserva
la cadena literal del archivo para no confundir una diferencia de presentación con una lectura.
La referencia incluye las propiedades completas y las envolventes de los ocho componentes
representados. Ninguna fila pendiente se considera comprobada en BIMvision por coincidir la
imagen general. No se declara aprobación de diseño, fidelidad frente a TR ni rendimiento.

Para cerrar el contraste hacen falta las lecturas observadas del recipiente y sus cotas en
BIMvision, con su unidad y evidencia de procedencia. Se ha solicitado esa lectura manual a Javier
porque no hay ventana controlable; no se sustituye por la extracción del IFC ni por una estimación
basada en píxeles de la captura.
