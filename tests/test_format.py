from ui.format import eur, num


def test_num_uses_dots_for_thousands():
    assert num(1_234_567) == "1.234.567"
    assert num(999) == "999"


def test_eur():
    assert eur(42_000) == "€ 42.000"
    assert eur(-1_240) == "€ -1.240"
    assert eur(0.4) == "€ 0"
