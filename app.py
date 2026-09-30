"""Glass Box Banking — Tectonic Hackathon, KBC-track.

Start: streamlit run app.py
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.config import ConfigError, Settings, configure_logging, merge_secrets
from engine.data import MARC_ID, generate_customers
from engine.future_self import PENSIOENLEEFTIJD, RENDEMENT, project, speak
from engine.mandate import DEMO_ACTIES, GEBLOKKEERD, UITGEVOERD, Mandaat, beslis
from engine.model import SITUATION_BY_NAME, THRESHOLD, explain, reasons_text, score_all

st.set_page_config(page_title="Glass Box Banking", page_icon="🔍", layout="wide")


def _secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # geen secrets.toml: prima, dan enkel omgevingsvariabelen
        return {}


@st.cache_resource
def get_settings() -> Settings:
    merge_secrets(_secrets(), os.environ)
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    return settings


try:
    settings = get_settings()
except ConfigError as exc:
    st.error(f"Configuratiefout: {exc}")
    st.stop()


@st.cache_data
def load(n: int):
    df = generate_customers(n)
    res, secs = score_all(df)
    return df, res, secs


st.title("Glass Box Banking")
st.caption("KBC herkent wie je nu bent, handelt binnen jouw regels en bewaakt wie je wordt. En legt altijd uit waarom. "
           "· Synthetische data, geen echte klanten.")

n = st.sidebar.select_slider("Aantal synthetische klanten", [1_000, 10_000, 100_000], value=10_000)
df, res, secs = load(n)
data = df.join(res[["situatie", "score"]])

st.sidebar.markdown("**Bekijk als klant**")
voorbeelden = {"Marc (58)": MARC_ID}
for sit in SITUATION_BY_NAME:
    ids = data.loc[data.situatie == sit, "klant_id"]
    if len(ids) and sit != "Pensioen in zicht":
        voorbeelden[f"Voorbeeld: {sit}"] = ids.iloc[0]
keuze = st.sidebar.selectbox("Klant", list(voorbeelden), label_visibility="collapsed")
klant = data.loc[data.klant_id == voorbeelden[keuze]].iloc[0]
naam = klant["naam"] or "Klant"

tab1, tab2, tab3, tab4 = st.tabs(["1 · Bankiersview", "2 · App van de klant", "3 · Future Self", "4 · Levensmandaat"])

# ---------------------------------------------------------------- 1. Bankiersview
with tab1:
    st.subheader("Understand + Scale: één uitlegbaar model over alle klanten")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Klanten gescoord", f"{len(data):,}".replace(",", "."))
    c2.metric("Doorlooptijd", f"{secs * 1000:.0f} ms")
    c3.metric("Met een levenssituatie", f"{(data.situatie != 'Geen bijzondere situatie').mean():.0%}")
    c4.metric("LLM-kost voor herkenning", "€0", help="Herkenning gebeurt met regels en gewichten, zonder LLM.")

    counts = data.loc[data.situatie != "Geen bijzondere situatie", "situatie"].value_counts()
    st.bar_chart(counts, horizontal=True, x_label="Aantal klanten", y_label="")

    st.markdown(f"**Hoe het model beslist** (drempel: score ≥ {THRESHOLD:.1f})")
    regels = [{"Situatie": s.naam, "Signaal": sig.uitleg, "Gewicht": sig.weight}
              for s in SITUATION_BY_NAME.values() for sig in s.signalen]
    with st.expander("Alle regels en gewichten bekijken"):
        st.dataframe(pd.DataFrame(regels), hide_index=True, width="stretch")

    st.markdown("**Klanten met een situatie, elk met hun redenen**")
    filt = st.selectbox("Filter op situatie", ["Alle"] + list(counts.index))
    view = data[data.situatie != "Geen bijzondere situatie"]
    if filt != "Alle":
        view = view[view.situatie == filt]
    view = pd.concat([data[data.klant_id == MARC_ID], view.head(50)]).drop_duplicates("klant_id")
    view = view.assign(redenen=[reasons_text(r, r.situatie) for _, r in view.iterrows()])
    st.dataframe(view[["klant_id", "naam", "leeftijd", "situatie", "score", "redenen"]],
                 hide_index=True, width="stretch")

# ---------------------------------------------------------------- 2. App van de klant
with tab2:
    st.subheader("Adapt: de homepage past zich aan, en legt uit waarom")
    left, right = st.columns([1, 1])
    sit_naam = klant.situatie
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
            ex = None

    with right:
        with st.container(border=True):
            st.caption(f"KBC Mobile · Goedemiddag, {naam}")
            st.metric("Zichtrekening", f"€ {klant.inkomen_pm - klant.uitgaven_pm + 1240:,.0f}".replace(",", "."))
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
            st.caption("Recente verrichtingen · Kaarten · Sparen")

# ---------------------------------------------------------------- 3. Future Self
with tab3:
    st.subheader("Future Self: praat met jezelf op 72")
    feiten = project(klant)
    a, b = feiten["scenario_a"], feiten["scenario_b"]
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown(f"**A · {a['omschrijving']}**")
        st.metric("Kapitaal bij pensioen", f"€ {a['kapitaal_bij_pensioen']:,}".replace(",", "."))
        st.metric("Extra per maand na pensioen", f"€ {a['extra_per_maand_na_pensioen']:,}".replace(",", "."))
    with c2, st.container(border=True):
        st.markdown(f"**B · {b['omschrijving']}**")
        st.metric("Kapitaal bij pensioen", f"€ {b['kapitaal_bij_pensioen']:,}".replace(",", "."),
                  delta=f"€ {b['kapitaal_bij_pensioen'] - a['kapitaal_bij_pensioen']:,}".replace(",", "."))
        st.metric("Extra per maand na pensioen", f"€ {b['extra_per_maand_na_pensioen']:,}".replace(",", "."),
                  delta=f"€ {feiten['verschil_per_maand_na_pensioen']}")
    st.caption(f"Aannames: pensioen op {PENSIOENLEEFTIJD}, {RENDEMENT:.0%} rendement per jaar, kapitaal verdeeld over 20 jaar. "
               "Een projectie, geen advies en geen product.")

    vraag = st.text_input("Vraag aan je toekomstige zelf (optioneel)", max_chars=300,
                          placeholder="Heb ik spijt gehad dat ik niet meer spaarde?")
    if st.button("Praat met mezelf op 72", type="primary"):
        with st.spinner("Je toekomstige zelf denkt na..."):
            st.session_state["fs"] = speak(feiten, vraag)
    fs = st.session_state.get("fs")
    if fs:
        with st.chat_message("assistant", avatar="🧓"):
            st.write(fs["tekst"])
        audio = Path("assets/future_self.mp3")
        if audio.exists():
            st.audio(str(audio))
        if fs["check_ok"]:
            getallen = ", ".join(map(str, fs["getallen"]))
            st.success(f"Cijfercheck OK: alle getallen ({getallen}) komen uit de berekening. Bron: {fs['bron']}.")
        else:
            st.warning(f"Cijfercheck: getallen {fs['fout']} kwamen niet uit de berekening. Getoond: {fs['bron']}.")
            if fs.get("geweigerd"):
                with st.expander("Geweigerde LLM-output"):
                    st.write(fs["geweigerd"])
    with st.expander("Wat Future Self weet (de enige input voor het LLM)"):
        st.json(feiten)

# ---------------------------------------------------------------- 4. Levensmandaat
with tab4:
    st.subheader("Het Levensmandaat: de klant schrijft de regels, de agent handelt erbinnen")
    links, r = st.columns([1, 1.4])
    with links, st.container(border=True):
        st.markdown(f"**Mandaat van {naam}**")
        m = Mandaat(
            buffer_maanden_min=st.slider("Noodbuffer nooit onder (maanden)", 1, 12, 3),
            vraag_boven=st.slider("Vraag eerst boven (€)", 100, 5000, 500, step=100),
            energie_auto_besparing=st.slider("Auto-overstap energie bij besparing vanaf (€/jaar)", 25, 500, 100, step=25),
            blokkeer_nieuwe_begunstigde_nacht=st.toggle("Groot bedrag 's nachts naar nieuwe begunstigde: blokkeren", True),
        )
        for i, regel in enumerate(m.regels(), 1):
            st.markdown(f"{i}. _{regel}_")
        getekend = st.checkbox(f"Ik, {naam}, keur deze regels goed.")

    with r:
        st.markdown("**Inkomende acties voor de agent**")
        if not getekend:
            st.info("Eerst het mandaat goedkeuren. Zonder mandaat handelt de agent niet.")
        else:
            if st.button("Laat de agent handelen", type="primary"):
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
