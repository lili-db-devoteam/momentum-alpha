"""Tab 2 · App van de klant: de homepage past zich aan, en legt uit waarom."""
from __future__ import annotations

import streamlit as st

from engine.model import SITUATION_BY_NAME, THRESHOLD, explain, look_ahead
from ui.context import DemoContext
from ui.format import eur


def render(ctx: DemoContext) -> None:
    klant, naam = ctx.klant, ctx.naam
    st.subheader("Adapt: de homepage past zich aan, en legt uit waarom")
    left, right = st.columns([1, 1])
    sit_naam = klant.situatie
    ex = None
    with left:
        st.markdown(f"**Klant:** {naam} · {int(klant.leeftijd)} jaar · `{klant.klant_id}`")
        if sit_naam in SITUATION_BY_NAME:
            sit = SITUATION_BY_NAME[sit_naam]
            st.markdown(f"**Herkend:** {sit_naam}  \n**Kanaal:** {sit.kanaal}  \n**Toon:** {sit.toon}")
            st.markdown("**Signalen die de klant zelf kan uitzetten:**")
            uit = set()
            for r in explain(klant, sit_naam)["redenen"]:
                if not r["actief"]:
                    continue
                aan = st.toggle(f"{r['uitleg']} (+{r['gewicht']:.2f})", value=True, key=f"sig_{klant.klant_id}_{r['key']}")
                if not aan:
                    uit.add(r["key"])
            ex = explain(klant, sit_naam, frozenset(uit))
        else:
            st.info("Geen bijzondere situatie: de homepage blijft standaard.")

    with right, st.container(border=True):
        st.caption(f"KBC Mobile · Goedemiddag, {naam}")
        st.metric("Zichtrekening", eur(klant.inkomen_pm - klant.uitgaven_pm + 1240))
        if ex and ex["toon_kaart"]:
            sit = SITUATION_BY_NAME[sit_naam]
            with st.container(border=True):
                st.caption("VOOR JOU, NU")
                titel = sit.kaart_titel.format(naam=f"{naam}, " if klant.naam else "")
                st.markdown(f"### {titel[0].upper() + titel[1:]}")
                st.write(sit.kaart_tekst)
                with st.expander("Waarom zie ik dit?"):
                    for r in ex["redenen"]:
                        if r["actief"] and not r["uitgezet"]:
                            st.progress(r["gewicht"], text=f"{r['uitleg']} (+{r['gewicht']:.2f})")
                    st.caption(f"Score {ex['score']:.2f} (drempel {THRESHOLD}). Berekend met regels, niet met een black box.")
        elif ex:
            st.success(f"Je zette signalen uit: score {ex['score']:.2f} is onder de drempel. Kate toont deze kaart niet meer.")
        for tip in look_ahead(klant):
            with st.container(border=True):
                st.caption("KATE'S TIPS · LOOKING AHEAD")
                st.markdown(f"### {tip['title']}")
                st.write(tip["text"])
                st.caption(f"Source: {tip['source']}")
                with st.expander("Why am I seeing this?"):
                    for reason in tip["reasons"]:
                        st.markdown(f"- `{reason}`")
        st.caption("Recente verrichtingen · Kaarten · Sparen")
