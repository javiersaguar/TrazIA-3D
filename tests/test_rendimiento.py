"""Las optimizaciones de rendimiento no cambian resultados: misma salida que el método original."""

import io

import numpy as np
import pytest


def test_distancias_de_superficie_iguales_que_trimesh():
    trimesh = pytest.importorskip("trimesh")
    pytest.importorskip("rtree")
    from trazia.families.metrics import _distance_to_surface

    rng = np.random.default_rng(7)
    for mesh in (trimesh.creation.icosphere(3), trimesh.creation.cylinder(0.6, 2.0, sections=48)):
        points = rng.normal(size=(600, 3)) * 1.5
        points = np.vstack((points, mesh.vertices, mesh.triangles_center))  # incluye empates
        expected = trimesh.proximity.closest_point(mesh, points)[1]
        assert np.array_equal(_distance_to_surface(mesh, points), expected)


def test_circulos_por_ventanas_iguales_que_hough_completo():
    cv2 = pytest.importorskip("cv2")
    from trazia.geometry2d.raster import _hough_circles

    k = 200 / 72
    image = np.zeros((1400, 2000), dtype=np.uint8)
    cv2.circle(image, (1503, 697), int(80 * k), 255, 3)
    cv2.circle(image, (400, 650), int(40 * k), 255, 3)
    cv2.line(image, (100, 100), (1900, 120), 255, 3)
    blurred = cv2.GaussianBlur(image, (5, 5), 1.5)
    full = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.5,
        minDist=200 * k,
        param1=120,
        param2=60,
        minRadius=int(25 * k),
        maxRadius=int(115 * k),
    )
    assert full is not None
    windowed = _hough_circles(blurred, k, None)
    assert sorted(map(tuple, full[0].tolist())) == sorted(tuple(map(float, c)) for c in windowed)
    # Una candidata dentro del alzado (x en puntos) se descarta igual que en find_plan.
    kept = _hough_circles(blurred, k, (400 / k - 10, 400 / k + 10))
    expected = [round(float(c[0])) for c in full[0] if c[0] > 1000]
    assert [round(float(c[0])) for c in kept] == expected


def test_png_de_cache_sin_perdida(tmp_path, monkeypatch):
    from PIL import Image

    from trazia import page_cache

    monkeypatch.setenv("TRAZIA_PAGE_CACHE", str(tmp_path))
    pixels = np.random.default_rng(1).integers(0, 255, size=(64, 96, 3), dtype=np.uint8)
    original = Image.fromarray(pixels)

    class Page:
        def to_image(self, resolution):
            return type("Rendered", (), {"original": original})()

    monkeypatch.setattr(page_cache, "path_for", lambda page, namespace, dpi: tmp_path / "p")
    first = page_cache.render_page(Page(), 200)  # calcula y guarda
    cached = page_cache.render_page(Page(), 200)  # lee el PNG guardado
    assert np.array_equal(np.asarray(first), pixels)
    assert np.array_equal(np.asarray(cached), pixels)
    assert Image.open(io.BytesIO((tmp_path / "p").read_bytes())).format == "PNG"


def test_precarga_se_desactiva_y_no_falla_sin_extras(monkeypatch):
    from trazia.runtime import warm_up

    monkeypatch.setenv("TRAZIA_WARMUP", "0")
    assert warm_up() == []
    monkeypatch.setenv("TRAZIA_WARMUP", "1")
    loaded = warm_up()
    assert "trazia.pipeline" in loaded and "pint" in loaded
