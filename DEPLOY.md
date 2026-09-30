# Deployen

## Nu: lokaal

Zie [README.md](README.md#draaien): `streamlit run app.py` of `docker compose up --build`.

Checklist vóór een demo:
- `pytest` groen.
- Key in `.env` (Docker) of `.streamlit/secrets.toml` (Python), of bewust zonder key.
- Eén keer de app openen zodat de 10.000 klanten gescoord en gecachet zijn.

Optionele audio (`assets/future_self.mp3`) zit niet in de Docker-image. Wil je die in Docker, voeg dan `COPY --chown=app:app assets ./assets` toe aan de Dockerfile.

## Configuratie

| Variabele | Standaard | Betekenis |
|---|---|---|
| `GEMINI_API_KEY` | leeg | Geen key: veilig sjabloon, alles werkt |
| `GEMINI_MODEL` | `gemini-2.5-flash` | |
| `GEMINI_TIMEOUT_S` | `15` | |
| `RATE_SESSION_MAX` | `5` | Gemini-calls per sessie per venster |
| `RATE_SESSION_WINDOW_S` | `600` | |
| `RATE_GLOBAL_PER_HOUR` | `60` | Gemini-calls per proces per uur |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` of `ERROR` |

Een ongeldige waarde stopt de app met een duidelijke foutmelding.

## Later: Google Cloud Run

Er is geen codewijziging nodig: de image leest `$PORT`, alle config komt uit
omgevingsvariabelen en de app bewaart geen state op schijf.

```bash
PROJECT_ID=<jouw-project>
REGION=europe-west1
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# Key in Secret Manager
printf '%s' "<GEMINI_API_KEY>" | gcloud secrets create gemini-key --data-file=-
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding gemini-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor

# Bouwen en deployen vanuit deze map
gcloud run deploy glassbox --source . --region $REGION \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini-key:latest \
  --max-instances 2 --session-affinity --timeout 3600 --memory 1Gi
```

Waarom deze vlaggen:
- `--session-affinity` en `--timeout 3600`: Streamlit houdt een WebSocket open per bezoeker.
- `--max-instances 2`: de globale Gemini-limiet geldt per instantie; zo blijft het plafond 2 × `RATE_GLOBAL_PER_HOUR`.
- Let op: een Gemini-call die mislukt door een timeout of netwerkfout wordt één keer opnieuw geprobeerd binnen dezelfde limiet-toelating. Reken voor het budget dus met maximaal 2 × RATE_GLOBAL_PER_HOUR calls per instantie per uur.
- `--allow-unauthenticated`: publieke demo. Wil je enkel het team toelaten, laat deze vlag weg en gebruik IAP of `gcloud run services proxy`.

Extra vangnet: zet in Google AI Studio (of de Cloud Console) een quotum/budget op de key.
