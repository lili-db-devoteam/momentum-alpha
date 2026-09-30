from ui.format import escape_md, eur, num


def test_num_uses_dots_for_thousands():
    assert num(1_234_567) == "1.234.567"
    assert num(999) == "999"


def test_eur():
    assert eur(42_000) == "€ 42.000"
    assert eur(-1_240) == "€ -1.240"
    assert eur(0.4) == "€ 0"


def test_escape_md_neutralises_links_and_latex():
    assert escape_md("[klik](http://x)") == r"\[klik\]\(http://x\)"
    assert escape_md("73.600 euro") == r"73\.600 euro"
    assert escape_md("$5 *vet*") == r"\$5 \*vet\*"
    assert escape_md("<b>") == r"\<b\>"
