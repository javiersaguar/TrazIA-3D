import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import plotly.graph_objects as go


def meshes_from_ifc(content: str) -> list[dict]:
    model = ifcopenshell.file.from_string(content)
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    meshes = []
    for product in model.by_type("IfcElement"):
        shape = ifcopenshell.geom.create_shape(settings, product)
        identity = ifcopenshell.util.element.get_psets(product).get("TrazIA_Identity", {})
        meshes.append(
            {
                "guid": product.GlobalId,
                "name": product.Name,
                "component": identity.get("ComponentId", product.Tag),
                "vertices": list(shape.geometry.verts),
                "faces": list(shape.geometry.faces),
            }
        )
    return meshes


def figure(meshes: list[dict], selected: str | None = None, changed: set | None = None):
    fig = go.Figure()
    colors = {
        "shell": "#85a9b6",
        "top_head": "#527c8b",
        "bottom_head": "#527c8b",
        "skirt": "#364f60",
    }
    for mesh in meshes:
        vertices, faces, component = mesh["vertices"], mesh["faces"], mesh["component"]
        color = "#f3ad4e" if changed and component in changed else colors.get(component, "#259a96")
        if component == selected:
            color = "#f3ad4e"
        fig.add_trace(
            go.Mesh3d(
                x=vertices[0::3],
                y=vertices[1::3],
                z=vertices[2::3],
                i=faces[0::3],
                j=faces[1::3],
                k=faces[2::3],
                color=color,
                opacity=0.35 if selected and component != selected else 1.0,
                name=mesh["name"],
                hovertemplate=mesh["name"] + "<extra></extra>",
                lighting={"ambient": 0.55, "diffuse": 0.8, "roughness": 0.45},
            )
        )
    axis = {"showbackground": False, "gridcolor": "#dbe4e8", "zerolinecolor": "#cbd5db"}
    fig.update_layout(
        height=570,
        margin={"l": 0, "r": 0, "b": 0, "t": 0},
        paper_bgcolor="#f5f8fa",
        scene={
            "aspectmode": "data",
            "xaxis": {**axis, "title": "X · m"},
            "yaxis": {**axis, "title": "Y · m"},
            "zaxis": {**axis, "title": "Z · m"},
            "camera": {"eye": {"x": 1.7, "y": -2.1, "z": 1.0}},
        },
        uirevision="trazia-camera",
        showlegend=False,
    )
    return fig
