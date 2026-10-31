import base64
import io
import zipfile
from xml.etree import ElementTree as ET

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from trazia.api.snapshots import router


def test_bcf_contains_actual_png_camera_and_guid_and_rejects_invalid_image():
    buffer = io.BytesIO()
    Image.new("RGB", (200, 100), "white").save(buffer, format="PNG")
    body = {
        "png_base64": base64.b64encode(buffer.getvalue()).decode(),
        "eye": [2, 3, 4],
        "target": [0, 0, 0],
        "up": [0, 1, 0],
        "zoom": 100,
        "viewport_height": 500,
        "guid": "0" * 22,
    }
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        result = client.post("/viewer/bcf", json=body)
        assert result.status_code == 200, result.text
        with zipfile.ZipFile(io.BytesIO(result.content)) as archive:
            png = next(name for name in archive.namelist() if name.endswith("snapshot.png"))
            assert archive.read(png) == buffer.getvalue()
            view = ET.fromstring(archive.read(png.replace("snapshot.png", "viewpoint.bcfv")))
            assert view.find(".//Component").attrib["IfcGuid"] == "0" * 22
            assert [float(view.find(f".//CameraViewPoint/{axis}").text) for axis in "XYZ"] == [
                2,
                -4,
                3,
            ]
            assert float(view.find(".//ViewToWorldScale").text) == 5
        assert client.post("/viewer/bcf", json={**body, "png_base64": "bad"}).status_code == 422
        assert client.post("/viewer/bcf", json={**body, "target": body["eye"]}).status_code == 422
