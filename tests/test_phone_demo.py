"""De HTML-demo spiegelt engine/*.py. Deze tests laten ze niet stilletjes uit elkaar lopen."""
import re
from pathlib import Path

from engine.future_self import EXTRA_SPAREN, PENSIOENLEEFTIJD, RENDEMENT, UITKEERJAREN
from engine.mandate import Mandaat
from engine.model import SITUATIONS, THRESHOLD

HTML = (Path(__file__).parents[1] / "demo" / "phone_demo.html").read_text(encoding="utf-8")


def _const(name: str) -> float:
    m = re.search(rf"\b{name}=([0-9.]+)", HTML)
    assert m, f"{name} niet gevonden in demo/phone_demo.html"
    return float(m.group(1))


def test_projection_assumptions_match_engine():
    assert _const("PENSIOEN") == PENSIOENLEEFTIJD
    assert _const("REND") == RENDEMENT
    assert _const("JAREN_UIT") == UITKEERJAREN
    assert _const("EXTRA") == EXTRA_SPAREN


def test_threshold_matches_engine():
    assert float(re.search(r"const THRESHOLD = ([0-9.]+)", HTML).group(1)) == THRESHOLD


def test_signal_weights_match_engine():
    for sit in SITUATIONS:
        for sig in sit.signalen:
            assert re.search(rf'\["{sig.key}",{str(sig.weight).lstrip("0")},', HTML), f"{sit.naam}/{sig.key}: gewicht wijkt af"


def test_mandate_defaults_match_engine():
    m = Mandaat()
    assert f"buffer:{m.buffer_maanden_min},vraag:{m.vraag_boven},energie:{m.energie_auto_besparing}" in HTML


def test_demo_has_no_secrets_or_external_calls():
    assert "api_key" not in HTML.lower() and "fetch(" not in HTML  # draait offline, geen LLM


def test_fullscreen_mode_shows_only_the_demo(monkeypatch):
    from streamlit.testing.v1 import AppTest

    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    at = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=60)
    at.query_params["demo"] = "1"
    at.run()
    assert not at.exception
    assert len(at.tabs) == 0 and len(at.sidebar.select_slider) == 0 and len(at.title) == 0
