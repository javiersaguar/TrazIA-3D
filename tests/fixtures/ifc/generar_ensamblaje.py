"""IFC4 sintético y mínimo con descomposición por ensamblajes (contrato C1 de las escenas 3D).

    uv run python tests/fixtures/ifc/generar_ensamblaje.py

Escribe `ensamblaje_proceso.ifc` junto a este archivo. Lo leen las pruebas del worker del visor
(web/src/workers/ifc-parse.test.ts) antes de que lleguen las plantas regeneradas:

- `P-900`: bomba raíz (IfcPump) SIN representación, con tres piezas agregadas
  (`P-900/carcasa`, `P-900/motor-a` con dos estilos y `P-900/bancada`);
- `L-01`: línea raíz (IfcElementAssembly) con un tramo agregado (`L-01/tramo-1`);
- `V-901`: equipo con geometría propia y sin piezas, como los IFC de proceso actuales.

Todo es sintético; las medidas de TrazIA_Dimensiones salen de las cajas que se dibujan.
"""

from pathlib import Path

import ifcopenshell
import ifcopenshell.api.context
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.unit

from trazia.ifc import stable_guid, validate_ifc

CODIGO = "SIM-ENS"
SALIDA = Path(__file__).with_name("ensamblaje_proceso.ifc")
COLORES = {
    "Acero": "#9eaebc",
    "Motor": "#2a5977",
    "Junta": "#343f45",
    "Hormigón": "#8b9293",
    "Gas": "#e7b44c",
}


def caja(centro, medidas):
    """Vértices y caras (triángulos) de una caja alineada con los ejes, Z arriba como en IFC."""
    cx, cy, cz = centro
    dx, dy, dz = (m / 2 for m in medidas)
    vertices = [
        (cx + sx * dx, cy + sy * dy, cz + sz * dz)
        for sz in (-1, 1)
        for sy in (-1, 1)
        for sx in (-1, 1)
    ]
    caras = [
        (1, 3, 4, 2),
        (5, 6, 8, 7),
        (1, 2, 6, 5),
        (3, 7, 8, 4),
        (1, 5, 7, 3),
        (2, 4, 8, 6),
    ]
    triangulos = [(a, b, c) for a, b, c, d in caras] + [(a, c, d) for a, b, c, d in caras]
    return vertices, triangulos


def main() -> None:
    model = ifcopenshell.file(schema="IFC4")
    model.header.file_name.name = SALIDA.name
    model.header.file_name.time_stamp = "2026-01-01T00:00:00"
    model.header.file_name.author = ("TrazIA-3D",)
    model.header.file_name.authorization = "DRAFT"

    def raiz(clase, clave, nombre, **atributos):
        entidad = ifcopenshell.api.root.create_entity(model, ifc_class=clase, name=nombre)
        entidad.GlobalId = stable_guid(f"{CODIGO}/{clave}")
        for campo, valor in atributos.items():
            setattr(entidad, campo, valor)
        return entidad

    proyecto = raiz("IfcProject", "project", CODIGO)
    unidades = [
        ifcopenshell.api.unit.add_si_unit(model, unit_type=tipo)
        for tipo in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT", "PLANEANGLEUNIT")
    ]
    ifcopenshell.api.unit.assign_unit(model, units=unidades)
    contexto = ifcopenshell.api.context.add_context(model, context_type="Model")
    cuerpo = ifcopenshell.api.context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=contexto,
    )

    def agregar(padre, hijos):
        # Relación explícita: ifcopenshell.api reordena y recoloca con conjuntos (no determinista).
        model.create_entity(
            "IfcRelAggregates",
            GlobalId=stable_guid(f"{CODIGO}/agregado/{padre.GlobalId}"),
            RelatingObject=padre,
            RelatedObjects=hijos,
        )

    sitio = raiz("IfcSite", "site", "Parcela sintética")
    edificio = raiz("IfcBuilding", "module", "Módulo de prueba")
    planta = raiz("IfcBuildingStorey", "deck", "Nivel de proceso")
    for padre, hijo in ((proyecto, sitio), (sitio, edificio), (edificio, planta)):
        agregar(padre, [hijo])

    origen = model.create_entity(
        "IfcLocalPlacement",
        RelativePlacement=model.create_entity(
            "IfcAxis2Placement3D",
            Location=model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
    )
    estilos = {}
    for nombre, color in COLORES.items():
        r, g, b = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
        colour = model.create_entity("IfcColourRgb", Name=nombre, Red=r, Green=g, Blue=b)
        shading = model.create_entity(
            "IfcSurfaceStyleShading", SurfaceColour=colour, Transparency=0.0
        )
        estilos[nombre] = model.create_entity(
            "IfcSurfaceStyle", Name=nombre, Side="BOTH", Styles=[shading]
        )

    def geometria(entidad, cajas):
        items = []
        for estilo, centro, medidas in cajas:
            vertices, triangulos = caja(centro, medidas)
            puntos = model.create_entity("IfcCartesianPointList3D", CoordList=vertices)
            malla = model.create_entity(
                "IfcTriangulatedFaceSet", Coordinates=puntos, Closed=True, CoordIndex=triangulos
            )
            model.create_entity("IfcStyledItem", Item=malla, Styles=[estilos[estilo]], Name=estilo)
            items.append(malla)
        representacion = model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=cuerpo,
            RepresentationIdentifier="Body",
            RepresentationType="Tessellation",
            Items=items,
        )
        entidad.ObjectPlacement = origen
        entidad.Representation = model.create_entity(
            "IfcProductDefinitionShape", Representations=[representacion]
        )

    def traza(entidad, clave, propiedades, dimensiones=None):
        pset = ifcopenshell.api.pset.add_pset(model, product=entidad, name="TrazIA_Traceability")
        pset.GlobalId = stable_guid(f"{CODIGO}/{clave}/trace")
        base = {"Dataset": "synthetic", "Draft": True, "ProcessProject": CODIGO, "Revision": "A"}
        ifcopenshell.api.pset.edit_pset(model, pset=pset, properties={**base, **propiedades})
        if dimensiones:
            medidas = ifcopenshell.api.pset.add_pset(
                model, product=entidad, name="TrazIA_Dimensiones"
            )
            medidas.GlobalId = stable_guid(f"{CODIGO}/{clave}/dimensiones")
            ifcopenshell.api.pset.edit_pset(model, pset=medidas, properties=dimensiones)

    raices = []
    bomba = raiz("IfcPump", "P-900", "P-900", Tag="P-900", Description="Bomba de prueba")
    bomba.ObjectPlacement = origen
    traza(
        bomba,
        "P-900",
        {
            "Component": "P-900",
            "Role": "equipment",
            "Description": "Bomba de prueba",
            "Service": "Agua de prueba",
        },
    )
    raices.append(bomba)
    piezas = (
        (
            "carcasa",
            "IfcBuildingElementProxy",
            "Carcasa",
            [("Acero", (0, 0, 1.0), (1.2, 0.8, 0.8))],
        ),
        (
            "motor-a",
            "IfcElectricMotor",
            "Motor A",
            [("Motor", (1.4, 0, 1.0), (1.0, 0.7, 0.7)), ("Junta", (0.85, 0, 1.0), (0.1, 0.5, 0.5))],
        ),
        ("bancada", "IfcSlab", "Bancada", [("Hormigón", (0.7, 0, 0.3), (2.6, 1.2, 0.6))]),
    )
    hijos = []
    for clave, clase, etiqueta, cajas in piezas:
        componente = f"P-900/{clave}"
        pieza = raiz(
            clase,
            componente,
            f"P-900 · {etiqueta}",
            Tag=componente,
            Description=etiqueta,
        )
        geometria(pieza, cajas)
        largo = max(m[0] for _, _, m in cajas)
        traza(
            pieza,
            componente,
            {
                "Component": componente,
                "ParentComponent": "P-900",
                "Role": "component",
                "Description": etiqueta,
            },
            {"LongitudM": float(largo)},
        )
        hijos.append(pieza)
    agregar(bomba, hijos)

    linea = raiz(
        "IfcElementAssembly",
        "L-01",
        "L-01",
        Tag="L-01",
        Description="Línea de prueba",
        PredefinedType="USERDEFINED",
        ObjectType="Línea de proceso",
    )
    linea.ObjectPlacement = origen
    traza(linea, "L-01", {"Component": "L-01", "Role": "pipe", "Fluid": "Gas"})
    raices.append(linea)
    tramo = raiz(
        "IfcPipeSegment",
        "L-01/tramo-1",
        "L-01 · Tramo 1",
        Tag="L-01/tramo-1",
        Description="Tramo 1",
    )
    geometria(tramo, [("Gas", (4.0, 0, 1.0), (4.0, 0.2, 0.2))])
    traza(
        tramo,
        "L-01/tramo-1",
        {
            "Component": "L-01/tramo-1",
            "ParentComponent": "L-01",
            "Role": "component",
            "Description": "Tramo 1",
        },
        {"LongitudM": 4.0, "DN": 150},
    )
    agregar(linea, [tramo])

    recipiente = raiz("IfcTank", "V-901", "V-901", Tag="V-901", Description="Recipiente sin piezas")
    geometria(recipiente, [("Acero", (-3.0, 0, 1.5), (1.5, 1.5, 3.0))])
    traza(recipiente, "V-901", {"Component": "V-901", "Role": "equipment"})
    raices.append(recipiente)

    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId=stable_guid(f"{CODIGO}/containment"),
        RelatedElements=raices,
        RelatingStructure=planta,
    )
    # Relaciones de Psets creadas por ifcopenshell.api: GUID y orden estables entre ejecuciones.
    for entidad in model.by_type("IfcRelDefinesByProperties"):
        entidad.GlobalId = stable_guid(f"{CODIGO}/relacion/{entidad.id()}")
    for asignacion in model.by_type("IfcUnitAssignment"):
        asignacion.Units = sorted(asignacion.Units, key=lambda unidad: unidad.id())
    problemas = validate_ifc(model)
    if problemas:
        raise ValueError(problemas[0]["message"])
    SALIDA.write_bytes(model.to_string().replace("\r\n", "\n").encode("utf-8"))
    print(f"{SALIDA.name}: {len(model.by_type('IfcProduct'))} productos")


if __name__ == "__main__":
    main()
