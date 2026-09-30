import pandas as pd
import pytest

from engine.data import MARC_ID, generate_customers
from engine.model import SITUATION_BY_NAME, explain, reasons_text, score_all


@pytest.fixture(scope="module")
def scored():
    df = generate_customers(10_000)
    res, secs = score_all(df)
    return df.join(res[["situatie", "score"]]), secs


def marc(data):
    return data.loc[data.klant_id == MARC_ID].iloc[0]


def test_generation_is_deterministic():
    pd.testing.assert_frame_equal(generate_customers(500), generate_customers(500))


def test_marc_is_retirement_case(scored):
    m = marc(scored[0])
    assert m.naam == "Marc"
    assert m.leeftijd == 58
    assert m.situatie == "Pensioen in zicht"
    assert m.score == pytest.approx(1.0)


def test_switching_off_signals_hides_card(scored):
    m = marc(scored[0])
    assert explain(m, "Pensioen in zicht")["toon_kaart"]
    ex = explain(m, "Pensioen in zicht", frozenset({"leeftijd_55", "nog_werkend"}))
    assert ex["score"] == pytest.approx(0.4)
    assert not ex["toon_kaart"]


def test_explain_matches_batch_score(scored):
    data = scored[0]
    sample = data[data.situatie != "Geen bijzondere situatie"].sample(200, random_state=1)
    for _, row in sample.iterrows():
        assert explain(row, row.situatie)["score"] == pytest.approx(row.score)


def test_every_situation_is_recognised_somewhere(scored):
    assert set(SITUATION_BY_NAME) <= set(scored[0].situatie)


def test_scores_10k_customers_under_one_second(scored):
    assert scored[1] < 1.0


def test_reasons_text(scored):
    m = marc(scored[0])
    assert "Je bent tussen 55 en 66 (+0.35)" in reasons_text(m, "Pensioen in zicht")
    assert reasons_text(m, "Geen bijzondere situatie") == ""
