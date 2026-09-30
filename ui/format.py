"""Weergavehelpers: Belgische getalnotatie op één plek."""
from __future__ import annotations

import re

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$])")


def num(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def eur(x: float) -> str:
    return f"€ {num(x)}"


def escape_md(text: str) -> str:
    """Maakt tekst veilig voor st.markdown: geen links, afbeeldingen, HTML of LaTeX."""
    return _MD_SPECIAL.sub(r"\\\1", text)
