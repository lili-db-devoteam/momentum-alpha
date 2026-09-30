# Glass Box Banking — hardening & deploy design

Date: 2026-09-30 · Status: draft for review

## Goal

Turn the hackathon prototype into a polished, secure demo that is easy to run
locally now and to deploy to Google Cloud Run later, without changing what the
audience sees (four tabs, Dutch UI, synthetic data). The demo content will
change later, so adding or changing a tab must be cheap.

## Decisions (agreed)

| Topic | Decision |
|---|---|
| Scope | Polished hackathon demo. No FastAPI split, no database, no accounts. |
| Deploy now | Local: `streamlit run app.py` or `docker compose up`. |
| Deploy later | Cloud Run. Must work without code changes (config via env, `$PORT`, stateless). Documented, not scripted. |
| Access | Fully public, no login. Gemini is protected by rate limits; the app never breaks when a limit is hit. |
| Extras | Hash-chained audit log with a "Probeer te knoeien" demo button. Strict LLM output check (no URLs/links/HTML; rendered as plain text). |
| Out of scope | New demo features, i18n, persistence, real KBC data, Streamlit Cloud as target. |

## Architecture

```
glassbox/
  app.py                 thin entry: page config, settings, sidebar, TABS registry → ui.*
  engine/                pure logic; MUST NOT import streamlit
    config.py            Settings (frozen dataclass) from env vars; validated; __repr__ hides key
    data.py              synthetic customers (unchanged)
    model.py             glass-box scoring (logic unchanged)
    mandate.py           mandate rules + decisions, input validation
    audit.py             hash-chained receipts + verify_chain()
    future_self.py       projection, prompt, output validation, speak(facts, question, llm)
    llm.py               Gemini client wrapper (timeout, 1 retry, sanitized errors)
    ratelimit.py         thread-safe sliding-window limiter
  ui/
    context.py           DemoContext dataclass passed to every tab (data, customer, settings, limiter)
    format.py            eur(), pct() helpers — single place for Belgian number formatting
    bankier.py, klantapp.py, future_self.py, mandaat.py   each exposes render(ctx) -> None
  tests/                 pytest (engine) + Streamlit AppTest smoke test
  Dockerfile, docker-compose.yml, .dockerignore, .env.example
  .streamlit/config.toml
  .github/workflows/ci.yml
  pyproject.toml         ruff + pytest config
  requirements.txt       pinned runtime deps; requirements-dev.txt adds pytest, ruff, pip-audit
  README.md, DEPLOY.md
```

### Extensibility

`app.py` holds one list:

```python
TABS = [("1 · Bankiersview", bankier.render), ("2 · App van de klant", klantapp.render), ...]
```

Adding a tab = one `ui/` module with `render(ctx)` + one line in `TABS`. The
smoke test iterates `TABS`, so new tabs are covered automatically.

### Config (`engine/config.py`)

`Settings.from_env()` reads environment variables. `app.py` first copies known
keys from `st.secrets` into the environment if present (local convenience); on
Docker / Cloud Run only env vars are used.

| Variable | Default | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | empty | No key → template text, app fully works |
| `GEMINI_MODEL` | `gemini-2.5-flash` | |
| `GEMINI_TIMEOUT_S` | `15` | |
| `RATE_SESSION_MAX` | `5` | Gemini calls per session per window |
| `RATE_SESSION_WINDOW_S` | `600` | |
| `RATE_GLOBAL_PER_HOUR` | `60` | Gemini calls per process per hour |
| `LOG_LEVEL` | `INFO` | |

Invalid values (non-numeric, ≤ 0) raise a clear error at startup. The key is
never included in `repr`, logs or error messages.

## Security

### Gemini rate limiting (`engine/ratelimit.py`)

- `SlidingWindowLimiter(max_calls, window_s, clock=time.monotonic)` with a
  `threading.Lock`; `try_acquire() -> (allowed: bool, retry_after_s: int)`.
- Global limiter: one instance via `st.cache_resource` (shared across sessions
  in the process). Session limiter: stored in `st.session_state`.
- A call proceeds only if **both** allow it (session checked first, so one
  user can't burn global budget after hitting their own limit).
- Identical (customer, question) pairs are cached per session: no new call.
- On limit: safe template shown with note
  "Limiet bereikt — veilige sjabloontekst getoond (opnieuw over N min)."
- Cloud Run note: global limit is per instance → deploy with `--max-instances=2`
  and an AI Studio quota on the key as backstop (documented in DEPLOY.md).

### LLM input/output (`engine/future_self.py`, `engine/llm.py`)

Input:
- Question truncated to 300 chars, control characters stripped.
- Question goes as the user message only; facts + rules live in the system prompt.

Output is **rejected** (template shown instead) when any check fails:
1. Contains a number not derivable from the facts (existing check).
2. Contains a URL (`http`, `www.`, bare domains like `x.com`), e-mail address,
   markdown link/image (`[..](..)`, `![`), or HTML tag.
3. Empty, or longer than 200 words.

Result object gains `reden` (which check failed). Rejected text is shown only
inside an expander, via `st.text` (never markdown). Accepted text is shown in
the chat bubble with all markdown special characters escaped
(`ui.format.escape_md()`), so it can never render as a link, image or HTML.

`llm.py`: `GeminiClient.generate(system, user) -> str` with timeout and one
retry on transient errors. Exceptions are mapped to a short category
(`timeout`, `quota`, `netwerk`, `onbekend`); raw messages are logged at DEBUG
without the key and never shown in the UI. `speak()` takes any object with
`generate()`, so tests use a fake.

### Audit trail (`engine/audit.py`)

- `Receipt` fields: existing decision fields + `tijd` (ISO-8601 UTC),
  `prev_hash`, `hash` (full SHA-256 hex of canonical JSON of all other fields,
  `sort_keys=True`, `ensure_ascii=False`). Genesis `prev_hash` = 64 zeros.
- `AuditLog.append(fields) -> Receipt`, `AuditLog.verify() -> (ok, first_bad_index | None)`.
- Detects: changed field, removed receipt, reordered receipts.
- UI shows a green "Keten geverifieerd (n ontvangstbewijzen)" or a red
  "Keten gebroken bij ontvangstbewijs #k". Hash shown shortened (12 chars) for
  readability; full hash in the audit-log table.
- **"Probeer te knoeien"** button: on a *copy* of the log, changes the amount
  in one receipt's text (e.g. €2.400 → €240) without recomputing hashes; the
  UI shows the verification turning red at that receipt. **"Herstel"** restores
  the original.
- `mandate.beslis()` returns decision fields; appending to the log is done by
  the caller, keeping decisions pure.

### Runtime hardening

- `.streamlit/config.toml`: `server.headless=true`, `server.enableXsrfProtection=true`,
  `server.enableCORS=false`, `server.maxUploadSize=1`,
  `browser.gatherUsageStats=false`, `client.showErrorDetails=false`,
  `client.toolbarMode="minimal"`.
- `load()` cache: `max_entries=3`.
- Dockerfile: `python:3.12-slim`, pinned deps, non-root user, `PORT` env
  (default 8501) used in the start command, `HEALTHCHECK` on `/_stcore/health`,
  no secrets baked in. `.dockerignore` excludes `.env`, `.streamlit/secrets.toml`,
  `.git`, tests caches.
- Logging: stdlib `logging`, one line per event (`llm_call`, `llm_rejected`,
  `rate_limited`, `llm_error`), key never logged, question logged truncated to 50 chars.
- Dependencies pinned in `requirements.txt`; CI runs `pip-audit`.

## Error handling

- No API key / limit reached / LLM error / rejected output → template text,
  with a visible, honest source label. The Future Self tab never errors.
- Startup config errors fail fast with a readable message.
- Unexpected exceptions: logged; user sees Streamlit's generic error (details hidden).

## Testing

All tests run offline, no API key.

- `test_model.py`: Marc → "Pensioen in zicht"; disabling signals drops below
  threshold; `explain()` score equals `score_all()` score for a sample of
  customers; 10k customers score in < 1 s.
- `test_mandate.py`: the four demo actions produce the expected decision;
  edges: hour 22 and 7 boundaries, buffer exactly at minimum, energy savings equal to threshold.
- `test_audit.py`: chain verifies; changed field / removed / reordered receipt
  detected at the correct index; tamper-copy leaves original intact.
- `test_future_self.py`: projection numbers stable for Marc; output check
  rejects invented numbers, URLs, e-mail, markdown links/images, HTML, >200
  words, empty; fake LLM returning junk / raising timeout → template; question
  with injection text is truncated and passed only as user message.
- `test_ratelimit.py`: session and global limits, sliding window with fake
  clock, `retry_after_s` correct, concurrent `try_acquire` from threads never
  exceeds `max_calls`.
- `test_config.py`: defaults, overrides, invalid values raise, key hidden in repr.
- `test_app.py`: `AppTest` runs `app.py`; every tab in `TABS` renders without
  exception for Marc and one example customer.

## Deploy

- **Local (now):**
  - `pip install -r requirements.txt && streamlit run app.py`
  - `cp .env.example .env` (optional key) then `docker compose up --build` → http://localhost:8501
  - Docker is not installed on the current dev machine; Docker build is verified in CI.
- **CI** (`.github/workflows/ci.yml`, on push/PR): ruff, pytest, pip-audit, docker build.
- **Later: Cloud Run** (DEPLOY.md section, commands only):
  `gcloud run deploy glassbox --source . --region europe-west1
  --set-secrets GEMINI_API_KEY=gemini-key:latest --max-instances 2
  --allow-unauthenticated`, plus Secret Manager setup and AI Studio quota.
  Streamlit needs WebSockets and session affinity (`--session-affinity`).

## README

Updated: what it does (unchanged table), run locally (3 ways), test/lint
commands, architecture, security section reflecting the above, honest
limitations.
