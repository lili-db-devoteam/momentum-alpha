# Glass Box Banking

**Tectonic Hackathon 2026 · KBC-challenge**

> Iedere AI weet straks wat je vandaag wil. Alleen KBC kan vechten voor wie je wordt.

KBC herkent wie je nu bent, handelt binnen jouw regels en bewaakt wie je wordt. En legt altijd uit waarom.

## Wat het doet

| Tab | Laag | Wat |
|---|---|---|
| 1 · Demo: Marc | Alle lagen | Eén scherm: links de telefoon van de klant, rechts de glass box. Situatie, signalen, projectie, cijfercheck en mandaatbeslissingen komen uit de Python-engine; de pagina verwoordt en tekent ze. Schermvullend via `/?demo=1`. |
| 2 · App van de klant | Adapt | De homepage toont een kaart die past bij de situatie, met kanaal en toon per situatie. "Waarom zie ik dit?" toont de signalen en gewichten; de klant kan elk signaal uitzetten en ziet de kaart verdwijnen. |
| 3 · Future Self | Hook | Python berekent twee scenario's. Gemini spreekt als de klant op 72, maar krijgt enkel die cijfers. Een cijfercheck weigert elke output met een getal dat niet uit de berekening komt. Geen productadvies. |
| 4 · Levensmandaat | Mandaat | Elk besluit krijgt een ontvangstbewijs in een hashketen; "Probeer te knoeien" toont hoe aanpassen meteen opvalt. |
| 5 · Bankiersview | Understand + Scale | Een uitlegbaar model (gewogen regels) scoort 10.000 synthetische klanten in milliseconden op levenssituatie. Elke klant krijgt zijn redenen mee. Geen LLM, dus geen LLM-kost voor herkenning. |

## Draaien

**Lokaal met Python (3.12+)**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt        # macOS/Linux: .venv/bin/python
cp .streamlit/secrets.toml.example .streamlit/secrets.toml     # optioneel: GEMINI_API_KEY invullen
.venv/Scripts/streamlit run app.py
```

**Met Docker**

```bash
cp .env.example .env        # optioneel: GEMINI_API_KEY invullen
docker compose up --build   # http://localhost:8501
```

Zonder API-key werkt alles; Future Self gebruikt dan een veilig sjabloon.
Optioneel: zet een ElevenLabs-opname in `assets/future_self.mp3`, dan speelt die af onder het antwoord.

Deployen naar Google Cloud Run: zie [DEPLOY.md](DEPLOY.md).

## Ontwikkelen

```bash
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest        # alle tests, offline, zonder key
.venv/Scripts/ruff check .            # lint
.venv/Scripts/pip-audit -r requirements.txt
```

CI (GitHub Actions) draait lint, tests, pip-audit en een Docker-build met healthcheck.

**Een tab toevoegen:** maak `ui/<naam>.py` met `render(ctx: DemoContext) -> None` en zet één regel in
`ui/registry.py`. De smoke test dekt hem automatisch.

## Architectuur

```
app.py                 dunne ingang: instellingen, caches, zijbalk, tabs
engine/                alle logica, importeert nooit streamlit (afgedwongen door een test)
  config.py            instellingen uit omgevingsvariabelen, gevalideerd
  data.py              synthetische klanten (+ Marc, 58)
  model.py             glass-box model: situaties = signalen met gewicht + uitleg
  mandate.py           mandaatregels en pure beslissingen
  audit.py             ontvangstbewijzen als hashketen
  future_self.py       deterministische projectie, prompt, outputcontrole
  llm.py               Gemini-wrapper: timeout, één retry, geen geheimen in fouten
  ratelimit.py         sliding-window limiet per sessie en globaal
ui/                    één module per tab + registry + weergavehelpers
tests/                 pytest + Streamlit AppTest
```

Principe: **het model beslist, het LLM formuleert alleen.**

## Veiligheid

| Risico | Maatregel |
|---|---|
| Iemand verbruikt de Gemini-key via de publieke URL | Max. 5 calls per sessie per 10 min en 60 per uur globaal (instelbaar). Daarna het veilige sjabloon. Zet ook een quotum op de key in Google AI Studio. |
| Prompt-injectie via de vraag | Vraag max. 300 tekens, stuurtekens verwijderd, enkel als user-bericht; regels en feiten staan in de systeemprompt. |
| LLM verzint cijfers of plaatst een (phishing)link | Output geweigerd bij een getal dat niet uit de berekening komt, een URL, e-mailadres, markdown-link, HTML, >200 woorden of lege tekst. Getoonde tekst wordt als platte tekst weergegeven. |
| Audit-log stil aanpassen | Hashketen (SHA-256, vorige hash in elk bewijs). Aanpassen, weghalen of herordenen wordt gedetecteerd. |
| Key lekt | Enkel via omgevingsvariabelen / `secrets.toml` (beide in `.gitignore` en `.dockerignore`); nooit in logs, `repr` of foutmeldingen. |
| Container-uitbraak | Docker-image draait als non-root, `no-new-privileges`, geen secrets in de image. |
| Browser-aanvallen | XSRF-bescherming aan, uploads uit, foutdetails verborgen voor gebruikers. |

## Eerlijk: wat niet af is

- Alle data is synthetisch; er is geen koppeling met echte KBC-systemen.
- Acties in het mandaat (energie-agent, betalingen) zijn gesimuleerd.
- In de demo-tab zijn de ontvangstbewijzen korte hashes die in de browser berekend worden. De echte hashketen met knoeidemo staat in tab 4.
- In de demo-tab spreekt Future Self met Gemini als er een API-key is, anders met het sjabloon; dat staat in de glass box bij "source". De tekst is Nederlands, de rest van de demo Engels.
- Zonder de Python-gegevens (HTML los geopend) valt de demo terug op een JavaScript-kopie van de engine.
- Het audit-log leeft in de browsersessie; een hashketen alleen kan niet zien dat het *laatste* bewijs is weggelaten. In productie hoort het anker (laatste hash) extern bewaard.
- De globale limiet geldt per proces; op Cloud Run dus per instantie.
- Aannames in de projectie (pensioen op 67, 3% rendement, 20 uitkeerjaren) zijn demo-waarden, geen advies.
- Buiten de demo (visie): agent-tot-agent-onderhandeling, collectieve intelligentie, nalatenschapsagent.
