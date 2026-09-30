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
    assert m.situatie == "Retirement in sight"
    assert m.score == pytest.approx(1.0)


def test_switching_off_signals_hides_card(scored):
    m = marc(scored[0])
    assert explain(m, "Retirement in sight")["toon_kaart"]
    ex = explain(m, "Retirement in sight", frozenset({"age_55_66", "still_working"}))
    assert ex["score"] == pytest.approx(0.4)
    assert not ex["toon_kaart"]


def test_explain_matches_batch_score(scored):
    data = scored[0]
    sample = data[data.situatie != "No specific situation"].sample(200, random_state=1)
    for _, row in sample.iterrows():
        assert explain(row, row.situatie)["score"] == pytest.approx(row.score)


def test_every_situation_is_recognised_somewhere(scored):
    assert set(SITUATION_BY_NAME) <= set(scored[0].situatie)


def test_scores_10k_customers_under_one_second(scored):
    assert scored[1] < 1.0


def test_reasons_text(scored):
    m = marc(scored[0])
    assert "Aged between 55 and 66 (+0.35)" in reasons_text(m, "Retirement in sight")
    assert reasons_text(m, "No specific situation") == ""


def test_threshold_matches_web_demo():
    from engine.model import THRESHOLD
    assert THRESHOLD == 0.65


def test_hospital_cover_column():
    df = generate_customers(10_000)
    working = (df.inkomen_pm > 2200) & (df.leeftijd < 67)
    assert df.hospital_cover_via_employer.dtype == bool
    assert not df.loc[~working, "hospital_cover_via_employer"].any()
    assert 0.65 < df.loc[working, "hospital_cover_via_employer"].mean() < 0.75
    assert df.loc[df.klant_id == MARC_ID, "hospital_cover_via_employer"].item()


def test_look_ahead_hospital_cover_for_marc(scored):
    from engine.model import look_ahead
    tips = look_ahead(marc(scored[0]))
    assert len(tips) == 1
    tip = tips[0]
    assert tip["title"] == "Marc, one more thing for later: your hospital cover."
    assert "rise sharply" in tip["text"]
    assert tip["source"] == "KBC Verzekeringen"
    assert tip["reasons"] == ["hospital_cover_via_employer = true", "years_to_retirement = 9 (≤ 10)"]


@pytest.mark.parametrize("leeftijd,cover,expected", [(57, True, 1), (56, True, 0), (66, True, 1), (60, False, 0)])
def test_look_ahead_window(scored, leeftijd, cover, expected):
    from engine.model import look_ahead
    row = marc(scored[0]).copy()
    row["leeftijd"], row["hospital_cover_via_employer"] = leeftijd, cover
    assert len(look_ahead(row)) == expected
