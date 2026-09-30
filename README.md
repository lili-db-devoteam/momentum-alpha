# Glass Box Banking

**Tectonic Hackathon 2026 · KBC-challenge**

> Iedere AI weet straks wat je vandaag wil. Alleen KBC kan vechten voor wie je wordt.

KBC herkent wie je nu bent, handelt binnen jouw regels en bewaakt wie je wordt. En legt altijd uit waarom.

## Wat het doet

| Tab | Laag | Wat |
|---|---|---|
| 1 · Bankiersview | Understand + Scale | Een uitlegbaar model (gewogen regels) scoort 10.000 synthetische klanten in milliseconden op levenssituatie. Elke klant krijgt zijn redenen mee. Geen LLM, dus geen LLM-kost voor herkenning. |
| 2 · App van de klant | Adapt | De homepage toont een kaart die past bij de situatie, met kanaal en toon per situatie. "Waarom zie ik dit?" toont de signalen en gewichten; de klant kan elk signaal uitzetten en ziet de kaart verdwijnen. |
| 3 · Future Self | Hook | Python berekent twee scenario's. Gemini spreekt als de klant op 72, maar krijgt enkel die cijfers. Een cijfercheck weigert elke output met een getal dat niet uit de berekening komt. Geen productadvies. |
| 4 · Levensmandaat | Mandaat | De klant keurt eigen regels goed. De agent handelt erbinnen: energiewissel automatisch, grote betaling eerst vragen, nachtelijke overschrijving naar nieuwe begunstigde geblokkeerd, buffer beschermd. Elke beslissing krijgt een ontvangstbewijs met hash in een audit-log. |

## Draaien

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # optioneel: GEMINI_API_KEY invullen
streamlit run app.py
```

Zonder API-key werkt alles; Future Self gebruikt dan een veilig sjabloon.
Optioneel: zet een ElevenLabs-opname in `assets/future_self.mp3`, dan speelt die af onder het antwoord.

## Architectuur

```
engine/data.py         synthetische klanten (+ Marc, 58)
engine/model.py        glass-box model: situaties = signalen met gewicht + uitleg
engine/future_self.py  deterministische projectie, LLM-prompt met guardrails, cijfercheck
engine/mandate.py      mandaatregels, beslissingen, ontvangstbewijzen
app.py                 Streamlit-UI
```

Principe: **het model beslist, het LLM formuleert alleen.**

## Veiligheid

- Geen API-keys in code of git: `st.secrets` / omgevingsvariabelen, `secrets.toml` staat in `.gitignore`.
- Geen login of klant-endpoints in deze demo; data is synthetisch en lokaal.
- LLM-input is beperkt (vaste systeemprompt, vraag max. 300 tekens) en LLM-output wordt gevalideerd voor hij getoond wordt.
- Mandaatbeslissingen zijn deterministisch en gelogd met een hash.

## Eerlijk: wat niet af is

- Alle data is synthetisch; er is geen koppeling met echte KBC-systemen.
- Acties in het mandaat (energie-agent, betalingen) zijn gesimuleerd.
- Aannames in de projectie (pensioen op 67, 3% rendement, 20 uitkeerjaren) zijn demo-waarden, geen advies.
- Buiten de demo (visie): agent-tot-agent-onderhandeling, collectieve intelligentie, nalatenschapsagent.
