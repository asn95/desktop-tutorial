# C3MR — Integrated Operational Management System

Web Admin Portal & Telegram Mini App Ecosystem for field collection operations.

Capstone Design Project · **Team Volvo** · Faculty of Artificial Intelligence and Smart
Manufacturing, President University · 2026

---

## The problem

Every month a branch manager at IndiHome by Telkomsel has to split hundreds of customer
visit targets across field officers, then track each visit until payment or follow-up.
Before this system that whole cycle lived in spreadsheets and chat messages: targets were
copied by hand, officers reported back as free text, and management only saw progress once
somebody finished a manual recap.

Three problems came out of that:

- **Scattered data** — no single source of truth
- **Slow assignment** — distributing hundreds of targets manually is repetitive and error-prone
- **No real-time visibility** — progress was only visible after a manual recap

One hard constraint shaped the whole design: field officers use their own phones, with very
mixed specifications, so anything requiring them to install a new app would not be adopted.

## What it does

| Channel | Who | How |
| --- | --- | --- |
| Web Admin Portal | Managers | React + TypeScript |
| Telegram Mini App | Field officers | Runs inside Telegram, nothing to install |
| Manager Bot | Managers | `/ask`, `/mingguan`, notifications |

On top of those, an AI assistant with **14 typed tools** answers operational questions and
performs assignment work, and an automated weekly report is delivered every Monday at
08.00 WIB.

## Architecture

```
CLIENTS                     SERVICES · Railway            DATA & INTELLIGENCE

Web Admin Portal ─┐      ┌─ c3mr-app ──────────┐      ┌─ PostgreSQL
React + TypeScript │      │  FastAPI REST API   │      │  6 tables · SQLAlchemy
                   ├──────┤  serves the web build├──────┤
Telegram Mini App ─┤      │  mounts /officer-app │      ├─ Anthropic Claude
vanilla JS         │      └──────────────────────┘      │  AI agent · 14 tools
                   │                                     │
Manager Bot ───────┘      ┌─ c3mr-bot ──────────┐      └─ External APIs
                          │  python-telegram-bot │         Nominatim · OSRM
                          │  weekly scheduler    │         Open-Meteo · Nager.Date
                          └──────────────────────┘
```

One database and one service layer: every channel, including the AI agent, goes through the
same code path, so no channel can reach a state the others cannot.

## Tech stack

**Backend** — Python, FastAPI, SQLAlchemy, PostgreSQL (SQLite for local development),
bcrypt, PyJWT, python-telegram-bot, Anthropic SDK

**Frontend** — React 18, TypeScript, Vite, Tailwind CSS, Leaflet

**Infrastructure** — Docker, Railway (two services), OpenStreetMap Nominatim, OSRM,
Open-Meteo, Nager.Date

## Repository layout

```
backend/
  main.py               FastAPI app, CORS, static mounts, 4 app-level endpoints
  models.py             6 tables and 3 enums — the whole schema
  security.py           JWT, bcrypt, Telegram HMAC validation, RBAC
  database.py           engine and session
  routers/              25 endpoints across 7 routers
  agent.py              the tool-use loop
  agent_tools.py        the 14 agent tools, priority scoring, distribution
  weekly_insight.py     Monday 08.00 WIB report
  bot_service.py        Telegram bot commands
  external.py           Nominatim, OSRM, Open-Meteo, Nager.Date
  tests/                26 tests

frontend/src/
  pages/                8 pages
  components/           layout and dashboard components
  contexts/             auth, theme, language
  lib/i18n.ts           Indonesian/English dictionary

mini-app/               officer Mini App (vanilla JS, served at /officer-app)
uml/images/             system, use case, sequence and component diagrams
```

## Getting started

Requires Python 3.11+ and Node 18+.

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env          # then fill it in, see below

uvicorn backend.main:app --reload --port 8000
```

```bash
# Frontend
cd frontend
npm install
npm run dev                   # dev server with hot reload
npm run build                 # production build, served by the backend
```

The Telegram bot runs as its own process:

```bash
python run_bot.py
```

### Environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `DATABASE_URL` | yes | PostgreSQL in production; falls back to local SQLite |
| `JWT_SECRET` | yes | signing key for access tokens |
| `CORS_ORIGINS` | yes | comma-separated allowed origins |
| `TELEGRAM_BOT_TOKEN` | yes | bot token from BotFather |
| `MINI_APP_URL` | yes | public URL of the officer Mini App |
| `ANTHROPIC_API_KEY` | yes | required by both services for the AI assistant |
| `MANAGER_BOT_ALLOWED_IDS` | no | extra Telegram IDs allowed to use manager commands |
| `SEED_TOKEN` | no | bootstraps the first administrator on a fresh deployment |
| `DEBUG` | no | `false` in production |

`SEED_TOKEN` only creates the first administrator and refuses to run once any manager
exists, so a leaked token cannot overwrite a live account. It is not a password reset path.

## Testing

```bash
pytest backend/tests -q
```

26 tests covering authentication, targets, assignment, RBAC, analytics, and a localization
check that keeps the Indonesian default honest and the translation dictionary free of dead
keys.

Beyond the automated suite, the system was validated with a **User Acceptance Test of 21
scenarios across 6 modules**, executed on the deployment by the client's own branch manager
and field officers.

## Security

- JWT access tokens expire after 4 hours; the role is re-checked against the database on
  every request, so a revoked account loses access on the next click
- Changing a password stamps `password_changed_at`, invalidating every token issued earlier
- Passwords are bcrypt-hashed with a per-user salt
- Login is rate limited server-side: 5 attempts per 60 seconds, tracked per client IP **and**
  per username, reading `X-Forwarded-For` so the limit works behind the platform proxy
- Officers have no password at all — identity comes from Telegram `initData`, verified with
  two-stage HMAC-SHA256, constant-time comparison, and a 300-second freshness window
- The AI agent cannot reach the database directly. It can only call one of 14 typed tools,
  each running parameterised queries, and there is no delete tool anywhere in the set

## Deployment

Two containers on Railway:

- **c3mr-app** — FastAPI API, serves the React build and mounts the Mini App
- **c3mr-bot** — Telegram bot and the Monday weekly report scheduler

Both read the same managed PostgreSQL instance. `ANTHROPIC_API_KEY` must be set on **both**
services: the web assistant runs in `c3mr-app` and `/ask` runs in `c3mr-bot`.

```bash
railway up --service c3mr-app
railway up --service c3mr-bot
```

## A note on the data

The customer records in this repository and in the running deployment are a **synthetic
dataset**, generated by `gen_dummy_agustus.py`. Loading real subscriber debt records into a
student-built system was not something we were authorised to do, so the data is generated
while the addresses are real streets, which keeps geocoding, the map, and distance-based
clustering behaving exactly as they would in production.

The deployment, the users, the workflow, the notifications and the latency are real. The
customer records are not.

## Team

| Member | Student ID | Role |
| --- | --- | --- |
| Auza Syamil Nabawi | 001202300150 | Lead · Frontend, UI security, and the entire AI layer |
| Rashad Abdul Faqih | 001202300149 | Backend, database, and infrastructure |
| Atthariqul Hazam Albanna | 012202300122 | Business analyst and QA |

Advisor: Dr. Adhi Setyo Santoso, S.T., M.B.A.

## License

Coursework produced for the Capstone Design Project at President University. Not licensed
for reuse.
