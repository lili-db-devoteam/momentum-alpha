"""De tabellen voor de telefoon-demo moeten exact dezelfde uitkomst geven als de engine zelf."""
import itertools

import pytest

from engine.data import MARC_ID, generate_customers
from engine.demo import ACTIES, BUFFERS, CODE, ENERGIE, VRAGEN, mandate_key, mandate_tables, scale_payload, trace_tables
from engine.mandate import Mandaat, beslis
from engine.model import SITUATIONS, explain, score_all

SALDO, UITGAVEN = 42_000.0, 3_150.0


@pytest.fixture(scope="module")
def tables():
    return mandate_tables(SALDO, UITGAVEN)


def test_lookup_equals_engine_for_every_mandate_setting(tables):
    """Volledige rooster: 12 buffers x 50 grenzen x 20 energiegrenzen x 2 nachtregels, voor alle 4 acties."""
    for b, v, e, n in itertools.product(BUFFERS, VRAGEN, ENERGIE, (False, True)):
        m = Mandaat(buffer_maanden_min=b, vraag_boven=v, energie_auto_besparing=e, blokkeer_nieuwe_begunstigde_nacht=n)
        for aid, actie in ACTIES.items():
            d = beslis(actie, m, SALDO, UITGAVEN)
            assert tables[aid][mandate_key(aid, m)] == [CODE[d["beslissing"]], d["regel"]], (aid, b, v, e, n)


def test_tables_are_small_enough_to_embed(tables):
    import json

    assert len(json.dumps(tables)) < 120_000


def test_trace_covers_every_switch_combination_and_matches_explain():
    df = generate_customers(1_000)
    marc = df.loc[df.klant_id == MARC_ID].iloc[0]
    tr = trace_tables(marc)
    assert len(tr) == 16
    assert tr[""]["show"] is True and tr[""]["score"] == 1.0
    all_off = ",".join(sorted(tr[""]["on"]))
    assert tr[all_off]["show"] is False and tr[all_off]["score"] == 0.0
    ex = explain(marc, "Pensioen in zicht", frozenset({"leeftijd_55"}))
    assert tr["leeftijd_55"]["score"] == ex["score"]


def test_scale_payload_counts_follow_situation_order():
    df = generate_customers(1_000)
    res, secs = score_all(df)
    data = df.join(res[["situatie", "score"]])
    p = scale_payload(data, secs)
    assert p["n"] == 1_000 and len(p["counts"]) == len(SITUATIONS)
    assert p["counts"][0] == int((data.situatie == SITUATIONS[0].naam).sum())
