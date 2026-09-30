"""Tab 1 · Bankiersview: één uitlegbaar model over alle klanten."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.data import MARC_ID
from engine.model import GEEN_SITUATIE, SITUATION_BY_NAME, THRESHOLD, reasons_text
from ui.context import DemoContext
from ui.format import num

KBC_KLANTEN = 2_300_000


def render(ctx: DemoContext) -> None:
    data = ctx.data
    st.subheader("Understand + Scale: één uitlegbaar model over alle klanten")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Klanten gescoord", num(len(data)))
    kbc_secs = ctx.score_secs / max(len(data), 1) * KBC_KLANTEN
    c2.metric("Doorlooptijd", f"{ctx.score_secs * 1000:.0f} ms", help="Lineaire extrapolatie van deze meting.")
    c2.caption(f"all 2.3M KBC customers ≈ {kbc_secs:.1f} s")
    c3.metric("Met een levenssituatie", f"{(data.situatie != GEEN_SITUATIE).mean():.0%}")
    c4.metric("LLM-kost voor herkenning", "€0", help="Herkenning gebeurt met regels en gewichten, zonder LLM.")

    counts = data.loc[data.situatie != GEEN_SITUATIE, "situatie"].value_counts()
    st.bar_chart(counts, horizontal=True, x_label="Aantal klanten", y_label="")

    st.markdown(f"**Hoe het model beslist** (drempel: score ≥ {THRESHOLD:.1f})")
    regels = [{"Situatie": s.naam, "Signaal": sig.uitleg, "Gewicht": sig.weight}
              for s in SITUATION_BY_NAME.values() for sig in s.signalen]
    with st.expander("Alle regels en gewichten bekijken"):
        st.dataframe(pd.DataFrame(regels), hide_index=True, width="stretch")

    st.markdown("**Klanten met een situatie, elk met hun redenen**")
    filt = st.selectbox("Filter op situatie", ["Alle", *counts.index], key="filter_situatie")
    view = data[data.situatie != GEEN_SITUATIE]
    if filt != "Alle":
        view = view[view.situatie == filt]
    view = pd.concat([data[data.klant_id == MARC_ID], view.head(50)]).drop_duplicates("klant_id")
    view = view.assign(redenen=[reasons_text(r, r.situatie) for _, r in view.iterrows()])
    st.dataframe(view[["klant_id", "naam", "leeftijd", "situatie", "score", "redenen"]],
                 hide_index=True, width="stretch")
