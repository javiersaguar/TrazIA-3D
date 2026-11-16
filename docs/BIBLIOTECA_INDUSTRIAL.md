# Biblioteca industrial de TrazIA-3D

La biblioteca contiene 72 diseños conceptuales de 18 familias, cuatro por familia.
Desde **Documentos → Familias** se puede desplegar cada ficha y abrir sus diseños.
Hay 56 parejas de lámina A3 e IFC4 DRAFT con componentes exteriores, además de los
16 bocetos PDF originales. Las cotas son sintéticas y describen la envolvente del modelo.

Para un diseño nuevo, las plantillas geométricas parten de parámetros conocidos. La
generación calcula las dos vistas del PDF y el IFC a partir de los mismos vértices. La
estrategia D del [estudio](ESTUDIO.md) se aplica a la extracción desde documentos existentes.
La biblioteca se mantiene fuera de los conjuntos de evaluación y entrenamiento.

| Familia | Variantes de la biblioteca | Referencia de la tipología |
| --- | --- | --- |
| Aeroenfriadores | Tiro inducido y tiro forzado con dos ventiladores | [Alfa Laval](https://www.alfalaval.com/products/heat-transfer/finned-tube-air-heat-exchangers/alfa-laval-olmi/) |
| Evaporadores | Película descendente y circulación forzada | [GEA](https://www.gea.com/en/assets/250176/) |
| Filtros industriales | Carcasa de bolsa simple y dúplex | [Eaton](https://www.eaton.com/us/en-us/catalog/filters-strainers/duoline.html) |
| Centrífugas | Decantadora horizontal y separador de discos | [GEA](https://www.gea.com/en/products/centrifuges-separation/) |
| Separadores ciclónicos | Individual y batería doble | [GEA](https://www.gea.com/en/products/product-handling-systems/storage-handling/raw-materials/self-cleaning-ciclone-filter-cfa/) |
| Secadores industriales | Atomización y lecho fluido | [GEA](https://www.gea.com/en/products/dryers-particle-processing/spray-dryers/fsd-spray-dryer/) |
| Mezcladores estáticos | En línea y con ramal de adición | [Sulzer](https://www.sulzer.com/-/media/files/products/static-mixers/flyer_smx_plus_d.pdf) |
| Módulos de dosificación | Panel simple y dúplex | [ProMinent](https://www.prominent.com/en/Products/Products/Metering-Systems/Metering-Systems-for-Liquids/p-dulcodos-panel-dswc.html) |
| Torres de refrigeración | Tiro inducido y tiro forzado | [SPX Cooling](https://spxcooling.com/cooling-towers/) |
| Mezcladores-decantadores | Una etapa y dos etapas | [Sulzer](https://solutions.sulzer.com/technologies/liquid-liquid-extraction-technology) |

Las referencias identifican la tipología. Los planos y las formas de la biblioteca son
propios, con geometría esquemática. Sirven para revisión visual e implantación preliminar,
sin cálculo de proceso, interiores funcionales ni detalle de fabricación.

## Regeneración

Desde la raíz, con las dependencias web instaladas:

```powershell
uv run --extra dev python scripts/make_industrial_designs.py
node web/scripts/export-industrial-ifc.mjs
```

Las plantillas editables están en `scripts/industrial_designs.py` y `scripts/design_variants.py`. El exportador vuelve a
abrir cada IFC con WebIFC y comprueba que todos sus componentes se pueden renderizar
antes de actualizar el índice. Estos IFC se abren en el visor de Documentos. Las nuevas
familias del catálogo no amplían el conjunto de plantillas de edición K.8.
