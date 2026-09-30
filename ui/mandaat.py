"""Tab 4 · Levensmandaat: de klant schrijft de regels, de agent handelt erbinnen."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.audit import AuditLog
from engine.mandate import DEMO_ACTIES, GEBLOKKEERD, UITGEVOERD, Mandaat, beslis
from ui.context import DemoContext

ICOON = {UITGEVOERD: "✅", GEBLOKKEERD: "⛔"}
ACTIES = {a.id: a for a in DEMO_ACTIES}
TE_KNOEIEN = 2  # A3, de verdachte nachtelijke overschrijving


def knoei(log: AuditLog) -> AuditLog:
    """Past één bedrag aan zonder de hash te herberekenen: wat een aanvaller zou doen."""
    i = min(TE_KNOEIEN, len(log) - 1)
    oud = log.receipts[i].fields["omschrijving"]
    nieuw = oud.replace("2.400", "240") if "2.400" in oud else f"{oud} (aangepast)"
    return log.tampered_copy(i, "omschrijving", nieuw)


def _knoei_cb(log_key: str, knoei_key: str) -> None:
    st.session_state[knoei_key] = knoei(st.session_state[log_key])


def _herstel_cb(knoei_key: str) -> None:
    st.session_state.pop(knoei_key, None)


def render(ctx: DemoContext) -> None:
    klant, naam = ctx.klant, ctx.naam
    log_key, knoei_key = f"audit_{klant.klant_id}", f"audit_knoei_{klant.klant_id}"
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
                log = AuditLog()
                for act in DEMO_ACTIES:
                    log.append(beslis(act, m, float(klant.spaargeld), float(klant.uitgaven_pm)))
                st.session_state[log_key] = log
                st.session_state.pop(knoei_key, None)
            if log_key in st.session_state:
                _toon_log(st.session_state[log_key], log_key, knoei_key)
    st.caption("Een fraudeur kan je bellen, maar niet door je mandaat heen.")


def _toon_log(log: AuditLog, log_key: str, knoei_key: str) -> None:
    geknoeid = knoei_key in st.session_state
    getoond: AuditLog = st.session_state[knoei_key] if geknoeid else log
    ok, slecht = getoond.verify()
    if ok:
        st.success(f"Keten geverifieerd ({len(getoond)} ontvangstbewijzen)")
    else:
        st.error(f"Keten gebroken bij ontvangstbewijs #{slecht + 1}: het log is achteraf aangepast.")
    k1, k2 = st.columns(2)
    k1.button("Probeer te knoeien", key="knoei", on_click=_knoei_cb, args=(log_key, knoei_key), disabled=geknoeid)
    k2.button("Herstel", key="herstel", on_click=_herstel_cb, args=(knoei_key,), disabled=not geknoeid)

    for i, r in enumerate(getoond.receipts):
        f = r.fields
        with st.container(border=True):
            st.markdown(f"{ICOON.get(f['beslissing'], '✋')} **{f['beslissing']}** · {f['omschrijving']}")
            if ACTIES[f["actie"]].context:
                st.caption(ACTIES[f["actie"]].context)
            st.markdown(f"Regel {f['regel']}: _{f['regeltekst']}_  \n{f['waarom']}")
            st.caption(f"Ontvangstbewijs #{i + 1} `{r.hash[:12]}` · vorige `{r.prev_hash[:12]}` · {f['tijd']}")
            if i == slecht:
                st.error("Deze hash klopt niet meer met de inhoud.")
    with st.expander("Audit-log (voor de klant én voor compliance)"):
        st.dataframe(pd.DataFrame(getoond.rows()).drop(columns=["mandaat"]), hide_index=True, width="stretch")
