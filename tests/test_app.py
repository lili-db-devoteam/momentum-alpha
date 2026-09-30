from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ui.registry import TABS

APP = str(Path(__file__).parents[1] / "app.py")


@pytest.fixture
def at(monkeypatch):
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    return app


def test_all_tabs_render_for_marc(at):
    assert not at.exception
    assert [t.label for t in at.tabs] == [label for label, _ in TABS]


@pytest.mark.parametrize("keuze", ["Voorbeeld: Terug van reis", "Voorbeeld: Fraudegevoelig moment", "Voorbeeld: Jonge ouder"])
def test_all_tabs_render_for_example_customer(at, keuze):
    at.selectbox(key="klant").set_value(keuze).run()
    assert not at.exception


def test_small_dataset_renders(at):
    at.select_slider(key="aantal").set_value(1_000).run()
    assert not at.exception
