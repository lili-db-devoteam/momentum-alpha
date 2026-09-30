"""web/index.html (hoofddemo) mag geen ruwe HTML-sinks gebruiken (Aikido: XSS)."""
import re
from pathlib import Path

HTML = (Path(__file__).parents[1] / "web" / "index.html").read_text(encoding="utf-8")


def test_web_demo_uses_no_raw_html_sinks():
    code = re.sub(r"/\*.*?\*/", "", HTML, flags=re.S)
    for sink in ("innerHTML", "outerHTML", "document.write", "insertAdjacentHTML", "createContextualFragment"):
        assert sink not in code, f"{sink} gevonden in web/index.html"
    calls = re.findall(r"setHTML\(([^,]+),(.{0,5})", code)
    assert calls, "setHTML wordt niet gebruikt"
    for target, arg in calls:
        if target.strip() == "el":  # de definitie zelf
            continue
        assert arg.startswith("html`"), f"setHTML({target}, ...) krijgt geen html`...`-fragment"


def test_web_demo_makes_no_network_calls():
    assert "fetch(" not in HTML and "XMLHttpRequest" not in HTML and "api_key" not in HTML.lower()
