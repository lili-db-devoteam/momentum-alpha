import os
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from engine.config import KNOWN_KEYS
from ui.registry import TABS

APP = str(Path(__file__).parents[1] / "app.py")


@pytest.fixture
def at(monkeypatch):
    saved_env = dict(os.environ)
    for key in KNOWN_KEYS:
        monkeypatch.delenv(key, raising=False)
    st.cache_resource.clear()
    app = AppTest.from_file(APP, default_timeout=60)
    app.secrets["GEMINI_API_KEY"] = ""  # niet-lege dict: AppTest leest het echte secrets.toml dan nooit
    app.run()
    yield app
    os.environ.clear()
    os.environ.update(saved_env)
    st.cache_resource.clear()


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


def _run_agent(at):
    at.checkbox(key="mandaat_ok").check().run()
    at.button(key="agent_handel").click().run()


def test_agent_log_verifies(at):
    _run_agent(at)
    assert not at.exception
    assert any("Keten geverifieerd (4 ontvangstbewijzen)" in s.value for s in at.success)


def test_tamper_demo_breaks_and_restores_chain(at):
    _run_agent(at)
    at.button(key="knoei").click().run()
    assert any("Keten gebroken bij ontvangstbewijs #3" in e.value for e in at.error)
    at.button(key="herstel").click().run()
    assert any("Keten geverifieerd" in s.value for s in at.success)
    assert not any("Keten gebroken" in e.value for e in at.error)


def test_receipts_are_per_customer(at):
    _run_agent(at)
    at.selectbox(key="klant").set_value("Voorbeeld: Terug van reis").run()
    assert not any("Keten geverifieerd" in s.value for s in at.success)


def test_future_self_without_key_shows_safe_template(at):
    at.button(key="fs_praat").click().run()
    assert not at.exception
    assert "Hey, ik ben jij, op 72" in at.chat_message[0].markdown[0].value
    assert any("Cijfercheck OK" in s.value for s in at.success)


def test_future_self_answer_is_per_customer(at):
    at.button(key="fs_praat").click().run()
    assert len(at.chat_message) == 1
    at.selectbox(key="klant").set_value("Voorbeeld: Terug van reis").run()
    assert len(at.chat_message) == 0


def test_suite_is_offline_and_uses_template(at):
    assert not os.environ.get("GEMINI_API_KEY")
    at.button(key="fs_praat").click().run()
    assert not at.exception
    assert any("sjabloon (geen API-key)" in s.value for s in at.success)
