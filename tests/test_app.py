from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "src" / "trazia" / "app.py"


def test_app_demo_and_review_gate():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not app.exception
    assert "Ingeniería" in app.title[0].value
    approve_button = next(b for b in app.button if b.label == "Aprobar esta versión")
    assert approve_button.disabled
    next(s for s in app.selectbox if s.label == "Caso de demostración").select("B")
    next(b for b in app.button if b.label == "Cargar demo sintética").click()
    app.run()
    assert not app.exception
    assert '"revision":"B"' in app.session_state["revision_json"]
    assert any(m.value == "4" for m in app.metric)
