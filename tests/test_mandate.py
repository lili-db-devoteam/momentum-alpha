from dataclasses import asdict

import pytest

from engine.mandate import DEMO_ACTIES, GEBLOKKEERD, UITGEVOERD, VRAAG, Actie, Mandaat, beslis, is_nacht

MARC = {"saldo": 42_000.0, "uitgaven_pm": 3_150.0}
M = Mandaat()


def actie(aid):
    return next(a for a in DEMO_ACTIES if a.id == aid)


@pytest.mark.parametrize("aid,beslissing,regel", [
    ("A1", UITGEVOERD, 3),
    ("A2", VRAAG, 2),
    ("A3", GEBLOKKEERD, 4),
    ("A4", GEBLOKKEERD, 1),
])
def test_demo_actions_for_marc(aid, beslissing, regel):
    b = beslis(actie(aid), M, **MARC)
    assert (b["beslissing"], b["regel"]) == (beslissing, regel)


@pytest.mark.parametrize("uur,nacht", [(21, False), (22, True), (23, True), (0, True), (6, True), (7, False)])
def test_night_boundaries(uur, nacht):
    assert is_nacht(uur) is nacht
    b = beslis(Actie("X", "t", "betaling", 2_400, nieuwe_begunstigde=True, uur=uur), M, **MARC)
    assert b["beslissing"] == (GEBLOKKEERD if nacht else VRAAG)


def test_buffer_exactly_at_minimum_is_not_blocked():
    b = beslis(Actie("X", "t", "overschrijving_spaargeld", 42_000 - 3 * 3_150, uur=11), M, **MARC)
    assert (b["beslissing"], b["regel"]) == (VRAAG, 2)


def test_buffer_one_euro_below_minimum_is_blocked():
    b = beslis(Actie("X", "t", "overschrijving_spaargeld", 42_000 - 3 * 3_150 + 1, uur=11), M, **MARC)
    assert (b["beslissing"], b["regel"]) == (GEBLOKKEERD, 1)


def test_energy_saving_equal_to_threshold_asks():
    b = beslis(Actie("X", "t", "energie", 0, besparing_per_jaar=100), M, **MARC)
    assert (b["beslissing"], b["regel"]) == (VRAAG, 3)


def test_night_rule_off_asks_instead_of_blocking():
    b = beslis(actie("A3"), Mandaat(blokkeer_nieuwe_begunstigde_nacht=False), **MARC)
    assert (b["beslissing"], b["regel"]) == (VRAAG, 2)


def test_small_payment_is_executed():
    b = beslis(Actie("X", "t", "betaling", 200), M, **MARC)
    assert (b["beslissing"], b["regel"]) == (UITGEVOERD, 2)


def test_decision_carries_rule_text_and_mandate_snapshot():
    b = beslis(actie("A2"), M, **MARC)
    assert b["regeltekst"] == M.regels()[1]
    assert b["mandaat"] == asdict(M)


def test_decision_is_pure():
    assert beslis(actie("A3"), M, **MARC) == beslis(actie("A3"), M, **MARC)
    assert "hash" not in beslis(actie("A3"), M, **MARC)


@pytest.mark.parametrize("kwargs", [{"buffer_maanden_min": 0}, {"buffer_maanden_min": 25},
                                    {"vraag_boven": -1}, {"energie_auto_besparing": -1}])
def test_invalid_mandate_rejected(kwargs):
    with pytest.raises(ValueError):
        Mandaat(**kwargs)


@pytest.mark.parametrize("kwargs", [{"uur": 24}, {"uur": -1}, {"bedrag": -5}, {"soort": "crypto"}, {"besparing_per_jaar": -1}])
def test_invalid_action_rejected(kwargs):
    base = {"id": "X", "omschrijving": "t", "soort": "betaling", "bedrag": 10}
    with pytest.raises(ValueError):
        Actie(**{**base, **kwargs})
