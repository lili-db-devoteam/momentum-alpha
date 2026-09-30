# Kate Forward

**Tectonic Hackathon 2026 · KBC challenge**

> Kate Forward turns KBC from a bank that reacts into a partner that looks ahead: it understands your life now, acts within rules you set, and helps build who you're becoming.

Every AI will soon know what you want today. Only KBC can fight for who you become. Kate Forward is a proof of concept for that idea, built around one principle: **the model decides, the LLM only words it.** Everything the customer sees can be explained ("Why am I seeing this?") and every automated decision leaves a tamper-evident receipt.

All data is synthetic. No real KBC systems or customer data are involved.

## See the demo in 30 seconds

You need nothing installed except a browser.

```bash
git clone https://github.com/lili-db-devoteam/momentum-alpha.git
cd momentum-alpha
open web/index.html        # macOS. Linux: xdg-open · Windows: start web/index.html
```

Or just double-click `web/index.html`. Chrome is recommended.

`web/index.html` is the pitch demo, a single self-contained HTML file with no server. The layout:

- **Left:** the customer's phone, showing what Marc (58) sees in his KBC app.
- **Right:** the "glass box", showing why: the signals, their weights, the projection and every mandate decision.
- **Top:** the four steps of the story: 1 · Recognize, 2 · Future Self, 3 · Life Mandate, 4 · Agent acts.

Things to try:

1. **Recognize:** open **Why am I seeing this?** and switch a signal off. The score drops below the threshold and the card on the phone disappears.
2. **Future Self:** click **Talk to yourself at 72** to see two retirement scenarios and what they mean for Marc.
3. **Life Mandate:** set your own rules with the sliders (emergency buffer, ask-first amount, energy switch) and approve them.
4. **Agent acts:** watch Kate's week. An energy switch goes through automatically, a large payment asks first, and a night-time transfer to a new beneficiary is blocked.

To ask Future Self a free-text question, use the Streamlit app below (tab 3).

## Run the full app (Python engine + Streamlit)

The Streamlit app runs the same story on the real Python engine. It adds a real Gemini call with a number check, the full hash-chained audit log with a tamper demo, and a banker view that scores 10,000 customers.

**Requirements:** Python 3.14 (tested) and optionally a Gemini API key. Without a key everything works and Future Self uses a safe template instead.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt     # Windows: .venv\Scripts\python
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # optional: fill in GEMINI_API_KEY
.venv/bin/streamlit run app.py
```

Open http://localhost:8501.

**With Docker instead:**

```bash
cp .env.example .env         # optional: fill in GEMINI_API_KEY
docker compose up --build    # http://localhost:8501
```

**Full-screen demo mode:** open http://localhost:8501/?demo=1 to show only the phone and the glass box, without the sidebar and tabs. This is best for screen recordings.

**Optional voice:** put an ElevenLabs recording at `assets/future_self.mp3` and it plays under the Future Self answer.

### What's in the app

The tab names are in Dutch, like the UI text.

| Tab | Layer | What it does |
|---|---|---|
| 1 · Demo: Marc | All layers | One screen: the customer's phone on the left, the glass box on the right. Situation, signals, projection, number check and mandate decisions all come from the Python engine. |
| 2 · App van de klant | Adapt | The home screen shows a card that fits the customer's situation, with a channel and tone per situation. "Why am I seeing this?" shows the signals and weights, and the customer can switch any signal off and watch the card disappear. A second card looks ahead: employer hospitalisation insurance ends at retirement. |
| 3 · Future Self | Hook | Python computes two scenarios. Gemini speaks as the customer at 72 but only receives those numbers. A number check rejects any output containing a figure that isn't in the calculation. No product advice. |
| 4 · Levensmandaat | Mandate | The customer approves their own rules and the agent acts within them: energy switch is automatic, large payment asks first, night-time transfer to a new beneficiary is blocked, buffer is protected. Every decision gets a receipt in a hash chain, and "Probeer te knoeien" (try to tamper) shows that any edit is noticed immediately. |
| 5 · Bankiersview | Understand + Scale | An explainable model (weighted rules) scores 10,000 synthetic customers in milliseconds on life situation. Each customer comes with their reasons. No LLM, so no LLM cost for recognition. |

### Two implementations, one set of rules

The web demo mirrors the Python engine in JavaScript: same rules, weights, threshold (0.65), formulas and mandate. The Python engine is the reference implementation. If you change a rule, change it in both places.

## Configuration

Settings come from environment variables, with `.streamlit/secrets.toml` as a fallback. Environment variables always win. Copy `.env.example` or `.streamlit/secrets.toml.example` for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | empty | Enables the real Gemini call. Empty means safe template. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model used for Future Self. |
| `GEMINI_TIMEOUT_S` | `15` | Timeout per call. |
| `RATE_SESSION_MAX` | `5` | Gemini calls per session per window. |
| `RATE_SESSION_WINDOW_S` | `600` | Window length in seconds. |
| `RATE_GLOBAL_PER_HOUR` | `60` | Gemini calls per hour for the whole process. |

## Development

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # all tests, offline, no key needed
.venv/bin/ruff check .              # lint
.venv/bin/pip-audit -r requirements.txt
```

CI (GitHub Actions) runs lint, tests, pip-audit and a Docker build with a health check.

**Dependencies (lockfile):** direct packages are listed in `requirements.in` and `requirements-dev.in`. `requirements.txt` and `requirements-dev.txt` are lockfiles: every package, including indirect ones, pinned with hashes for every platform. Never edit them by hand; regenerate them with [uv](https://docs.astral.sh/uv/):

```bash
uv pip compile --universal --generate-hashes --python-version 3.14 requirements.in -o requirements.txt
uv pip compile --universal --generate-hashes --python-version 3.14 -c requirements.txt requirements-dev.in -o requirements-dev.txt
```

**Adding a tab:** create `ui/<name>.py` with `render(ctx: DemoContext) -> None` and add one line to `ui/registry.py`. The smoke test covers it automatically.

**Deploying** to Google Cloud Run: see [DEPLOY.md](DEPLOY.md) (written in Dutch).

## Architecture

```
web/index.html         the pitch demo: one static file, JavaScript mirror of the engine
app.py                 thin entry point: settings, caches, sidebar, tabs
engine/                all logic, never imports streamlit (enforced by a test)
  config.py            settings from environment variables, validated
  data.py              synthetic customers (plus Marc, 58)
  model.py             glass-box model: situations = signals with weight + explanation
  mandate.py           mandate rules and pure decisions
  audit.py             receipts as a hash chain
  future_self.py       deterministic projection, prompt, output check
  llm.py               Gemini wrapper: timeout, one retry, no secrets in errors
  ratelimit.py         sliding-window limit per session and global
ui/                    one module per tab, plus registry and display helpers
tests/                 pytest and Streamlit AppTest
```

## Security

| Risk | Mitigation |
|---|---|
| Someone burns the Gemini key through the public URL | At most 5 calls per session per 10 minutes and 60 per hour globally (configurable), then the safe template. Also set a quota on the key in Google AI Studio. |
| Prompt injection via the question | Question capped at 300 characters, control characters stripped, sent only as a user message; rules and facts live in the system prompt. |
| LLM invents numbers or posts a (phishing) link | Output rejected on any number not from the calculation, URL, email address, markdown link, HTML, more than 200 words, or empty text. Shown text is rendered as plain text. |
| Audit log silently edited | Hash chain (SHA-256, previous hash in every receipt). Editing, removing or reordering is detected. |
| Key leaks | Only via environment variables or `secrets.toml` (both in `.gitignore` and `.dockerignore`); never in logs, `repr` or error messages. |
| Container escape | Docker image runs as non-root with `no-new-privileges`; no secrets in the image. |
| Browser attacks | XSRF protection on, uploads off, error details hidden from users. |

## What's not finished

- All data is synthetic; there is no link to real KBC systems.
- Mandate actions (energy agent, payments) are simulated.
- In `web/index.html` and in the Streamlit demo tab, receipts are short hashes computed in the browser without a chain. The real hash chain with the tamper demo is in Streamlit tab 4.
- In the demo tab, Future Self uses Gemini if an API key is set and the template otherwise; the glass box shows which under "source".
- Opened on its own, the HTML demo falls back to a JavaScript copy of the engine instead of the Python data.
- The audit log lives in the browser session. A hash chain alone cannot show that the *last* receipt was omitted; in production the anchor (last hash) must be stored externally.
- The global rate limit is per process, so on Cloud Run it is per instance.
- The hospitalisation-insurance look-ahead is a single rule; there is no real policy data.
- Projection assumptions (retirement at 67, 3% return, 20 payout years) are demo values, not advice.
- Out of scope, part of the vision: agent-to-agent negotiation, collective intelligence, an estate agent.
