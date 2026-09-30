"""Tab 4 · Levensmandaat: de klant schrijft de regels, de agent handelt erbinnen."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.mandate import DEMO_ACTIES, GEBLOKKEERD, UITGEVOERD, Mandaat, beslis
from ui.context import DemoContext


def render(ctx: DemoContext) -> None:
    klant, naam = ctx.klant, ctx.naam
    st.subheader("Het Levensmandaat: de klant schrijft de regels, de agent handelt erbinnen")
    left, right = st.columns([1, 1.4])
    with left, st.container(border=True):
        st.markdown(f"**Mandaat van {naam}**")
        m = Mandaat(
            buffer_maanden_min=st.slider("Noodbuffer nooit onder (maanden)", 1, 12, 3, key="m_buffer"),
            vraag_boven=st.slider("Vraag eerst boven (€)", 100, 5000, 500, step=100, key="m_vraag"),
            energie_auto_besparing=st.slider("Auto-overstap energie bij besparing vanaf (€/jaar)", 25, 500, 100, step=25,
                                             key="m_energie"),
            blokkeer_nieuwe_begunstigde_nacht=st.toggle("Groot bedrag 's nachts naar nieuwe begunstigde: blokkeren", True,
                                                        key="m_nacht"),
        )
        for i, regel in enumerate(m.regels(), 1):
            st.markdown(f"{i}. _{regel}_")
        getekend = st.checkbox(f"Ik, {naam}, keur deze regels goed.", key="mandaat_ok")

    with right:
        st.markdown("**Inkomende acties voor de agent**")
        if not getekend:
            st.info("Eerst het mandaat goedkeuren. Zonder mandaat handelt de agent niet.")
        else:
            if st.button("Laat de agent handelen", type="primary", key="agent_handel"):
                st.session_state["log"] = [beslis(act, m, float(klant.spaargeld), float(klant.uitgaven_pm))
                                           for act in DEMO_ACTIES]
            acties = {a.id: a for a in DEMO_ACTIES}
            for bw in st.session_state.get("log", []):
                icon = "✅" if bw["beslissing"] == UITGEVOERD else ("⛔" if bw["beslissing"] == GEBLOKKEERD else "✋")
                with st.container(border=True):
                    st.markdown(f"{icon} **{bw['beslissing']}** · {bw['omschrijving']}")
                    if acties[bw["actie"]].context:
                        st.caption(acties[bw["actie"]].context)
                    st.markdown(f"Regel {bw['regel']}: _{bw['regeltekst']}_  \n{bw['waarom']}")
                    st.caption(f"Ontvangstbewijs `{bw['hash']}` · {bw['tijd']}")
            if st.session_state.get("log"):
                with st.expander("Audit-log (voor de klant én voor compliance)"):
                    st.dataframe(pd.DataFrame(st.session_state["log"]).drop(columns=["mandaat"]),
                                 hide_index=True, width="stretch")
    st.caption("Een fraudeur kan je bellen, maar niet door je mandaat heen.")
