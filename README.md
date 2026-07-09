# LoL Coach

A local desktop application that turns your League of Legends match history into
a structured, data-driven coaching program — without AI services, cloud accounts,
or external dependencies beyond the Riot Games API.

LoL Coach pulls your matches, scores each game across role-specific performance
dimensions, identifies where losses are actually happening, and generates a
focused training plan with exercises that complete automatically from real game
data. Every recommendation is derived from your own history, not population
averages.

**Who is it for?** Players who want to improve with precision, not guesswork.  
**What makes it different?** The entire coaching loop — from raw match data to a
concrete daily exercise — runs locally on your machine using deterministic rules
and your own performance distribution as the baseline.

> No LLMs. No external coaching services. No subscription.  
> Just your data, a scoring engine, and a rule system that knows what to fix.

---

## Table of Contents

- [Project Status](#project-status)
- [Features](#features)
- [Architecture](#architecture)
- [How Data Flows](#how-data-flows)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Project Structure](#project-structure)
- [Engines](#engines)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Vision](#vision)
- [License](#license)

---

## Project Status

| Component | Status | Notes |
|---|---|---|
| FastAPI backend | Stable | 15 endpoints, versioned at `/api/v1` |
| React + Electron frontend | Stable | 8 feature pages, production-ready |
| Scorer V2 | Stable | ADC and TOP roles fully implemented |
| Priority Engine | Stable | Win/loss delta ranking |
| Knowledge Engine | Stable | Memory, patterns, insights, recommendations |
| Training Engine | Stable | Skill tree with auto-evaluating exercises |
| Draft Engine | Stable | LCU integration + WebSocket stream |
| Match Review | Stable | Per-game breakdown with dimension scores |
| Progress Tracking | Stable | Weekly goals, habits, trend analysis |
| MID / JUNGLE / SUPPORT roles | Planned | Scorer architecture already supports them |
| Auto-start backend from Electron | Planned | Currently requires a separate terminal |

Test suite: **385 tests passing** across 8 files.

---

## Features

| Feature | Description |
|---|---|
| **Performance Dashboard** | Overall score, recent trend, and rank at a glance |
| **Match Review** | Per-game breakdown of every scored dimension and key metric |
| **Coaching Engine** | Rule-based recommendations derived from your win/loss patterns |
| **Champion Coach** | Classifies each champion as Main / Growth Pick / Risk Pick |
| **Priority Engine** | Ranks skills by estimated win-rate impact using match deltas |
| **Knowledge Engine** | Detects behavioral patterns and maintains an adaptive goal across sessions |
| **Training Engine** | Skill tree with exercises that auto-complete from post-game data |
| **Draft Intelligence** | Contextual draft analysis with live WebSocket updates |
| **Progress Tracking** | Weekly goal, performance habits, and multi-week trend data |
| **Settings + Sync** | API key management, region selection, and incremental match sync |

Roles currently scored: **ADC**, **TOP**.

---

## Architecture

```
╔══════════════════════════════════════════╗
║           Electron Shell (v33)            ║
║  ┌────────────────────────────────────┐  ║
║  │  React 18 · TypeScript · Vite       │  ║
║  │  TanStack Query v5 · Zustand        │  ║
║  │  Framer Motion · Radix UI           │  ║
║  └────────────────┬───────────────────┘  ║
╚═══════════════════╪══════════════════════╝
                    │
          HTTP REST + WebSocket
              127.0.0.1:8766
                    │
╔═══════════════════╪══════════════════════╗
║        FastAPI · Pydantic v2              ║
║   ┌───────────────────────────────────┐  ║
║   │  Routes (transport only)           │  ║
║   │  No business logic in routes       │  ║
║   └───────────────┬───────────────────┘  ║
║                   │                       ║
║   ┌───────────────▼───────────────────┐  ║
║   │  ViewModels (orchestration layer)  │  ║
║   └───────────────┬───────────────────┘  ║
║                   │                       ║
║   ┌───────────────▼───────────────────┐  ║
║   │  Engines                           │  ║
║   │  scorer_v2 · coaching_engine       │  ║
║   │  priority_engine · knowledge/      │  ║
║   │  training/ · draft/                │  ║
║   └───────────────┬───────────────────┘  ║
╚═══════════════════╪══════════════════════╝
                    │
╔═══════════════════╪══════════════════════╗
║           SQLite  │  db.py                ║
║   config · player · match · analysis      ║
╚═══════════════════╪══════════════════════╝
                    │
         ┌──────────┴──────────┐
         │                     │
╔════════╪════════╗   ╔════════╪════════════╗
║  Riot Games API  ║   ║  LCU (local client) ║
║  REST · cached   ║   ║  lockfile · HTTPS   ║
╚═════════════════╝   ╚════════════════════╝
```

**Design constraints enforced across the codebase:**
- Routes call a ViewModel and serialize. Nothing else.
- ViewModels orchestrate engines and read from `db.py`. No HTTP logic.
- Engines are stateless functions. State lives in `db.py` or the training JSON blob.
- The React frontend owns zero business logic. Everything comes from the API.

---

## How Data Flows

```
  League client plays a game
           │
           ▼
  ┌─────────────────────┐
  │    Riot Games API    │   GET /lol/match/v5/matches/{id}
  └──────────┬──────────┘
             │  raw JSON (~200 fields per participant)
             ▼
  ┌─────────────────────┐
  │      parser.py       │   extracts the 38 relevant fields
  └──────────┬──────────┘   for the tracked PUUID
             │
             ▼
  ┌─────────────────────┐
  │       db.py          │   INSERT OR IGNORE into match table
  │  SQLite · 4 tables   │   additive schema migrations on startup
  └──────────┬──────────┘
             │
       ┌─────┴──────────────────────────┐
       │                                │
       ▼                                ▼
  ┌──────────────┐             ┌──────────────────┐
  │  scorer_v2   │             │ priority_engine   │
  │              │             │                   │
  │ score_match()│             │ compute_priorities│
  │ per game     │             │ ranks metrics by  │
  │              │             │   win/loss delta  │
  │ analyze_     │             └────────┬─────────┘
  │ player()     │                      │
  │ aggregates   │                      │
  └──────┬───────┘                      │
         └─────────────┬────────────────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
   ┌─────────────────┐  ┌────────────────────┐
   │  knowledge/      │  │  training/          │
   │  engine.py       │  │  engine.py          │
   │                  │  │                     │
   │  session summary │  │  selects active     │
   │  adaptive goal   │  │    skill            │
   │  pattern detect  │  │  generates exercise │
   │  recommendations │  │  evaluates progress │
   └────────┬────────┘  │  auto-advances tree │
            │            └────────┬───────────┘
            └─────────┬───────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │     ViewModels       │
           │  assembles response  │
           │  objects from engine │
           │  outputs             │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   FastAPI routes     │
           │  serialize to JSON   │
           │  via Pydantic schemas│
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │  React + TanStack Q  │
           │  renders data as-is  │
           │  no transformation   │
           └─────────────────────┘
```

---

## Tech Stack

### Backend

| Package | Version | Role |
|---|---|---|
| Python | 3.10+ | Runtime |
| FastAPI | ≥ 0.110 | REST API + WebSocket server |
| uvicorn | ≥ 0.29 | ASGI server |
| Pydantic v2 | ≥ 2.6 | Schema validation |
| websockets | ≥ 12.0 | Draft real-time stream |
| requests | ≥ 2.32 | Riot API HTTP client |
| python-dotenv | ≥ 1.0 | Environment configuration |

### Frontend

| Package | Version | Role |
|---|---|---|
| Electron | 33 | Desktop shell (Windows + macOS) |
| React | 18.3 | UI framework |
| TypeScript | 5.7 | Type safety |
| electron-vite | 2.3 | Build toolchain |
| TanStack Query | v5 | Server state, caching, polling |
| Framer Motion | 11 | Animations |
| Tailwind CSS | 3.4 | Utility-first styling |
| Radix UI | — | Accessible headless primitives |
| Zustand | 4.5 | Client-side global state |
| Axios | 1.7 | HTTP client |
| React Router | v6 | In-app routing (HashRouter) |
| Lucide React | 0.468 | Icon system |

### Storage

| Technology | Detail |
|---|---|
| SQLite | Single file: `data/lol_coach.db` |
| Tables | `config`, `player`, `match` (38 columns), `analysis` |
| Migrations | Additive column additions via `PRAGMA table_info`, no data loss |
| JSON blobs | Training state and knowledge memory stored as JSON in `config` table |

### Testing

| Package | Version | Role |
|---|---|---|
| pytest | ≥ 8.0 | Test runner |
| httpx | ≥ 0.27 | `TestClient` for FastAPI (via Starlette) |

### External APIs

| API | Protocol | Usage |
|---|---|---|
| Riot Games REST API | HTTPS | Match history, account, summoner, league data |
| LCU (League Client Update) | HTTPS (local) | Live champion select state from the League client |

---

## Prerequisites

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Riot Games API key** — [developer.riotgames.com](https://developer.riotgames.com/)
  - Personal keys (free) expire every 24 hours.
  - Production keys (require application approval) do not expire.

---

## Installation

### 1. Clone

```bash
git clone https://github.com/your-username/lol-coach.git
cd lol-coach
```

### 2. Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Environment

Create `frontend/.env`:

```env
VITE_API_PORT=8766
```

The port must match the one passed to uvicorn. Change both if `8766` is in use on your machine.

---

## Running the App

The backend and frontend are separate processes. Start them in two terminals.

**Terminal 1 — backend**

```bash
uvicorn backend.api.main:app --host 127.0.0.1 --port 8766
```

Interactive API docs: `http://127.0.0.1:8766/docs`

**Terminal 2 — frontend (development)**

```bash
cd frontend
npm run dev
```

This opens the Electron window with hot reload enabled.

---

### First launch

Open **Settings**, enter your Riot Games API key, Riot ID (`GameName#TAG`),
and region. Then click **Sync** to download your match history.

Supported regions: LA1 · LA2 · NA1 · EUW1 · EUN1 · BR1 · KR · JP1 · OC1

---

### Build a distributable

```bash
cd frontend
npm run package
```

Output in `frontend/dist/`:
- **Windows** — NSIS installer (`.exe`)
- **macOS** — DMG image (`.dmg`)

---

### Legacy interface (Streamlit)

The original Streamlit interface still works and does not require the backend:

```bash
streamlit run main.py
```

---

## Project Structure

```
lol-coach/
│
├── backend/
│   ├── api/
│   │   ├── routes/          # One file per endpoint group. Transport only —
│   │   │                    # each handler calls a ViewModel and returns.
│   │   ├── schemas/         # Pydantic request and response models.
│   │   ├── websocket/       # Draft WebSocket connection manager.
│   │   ├── middleware/       # Request logging middleware.
│   │   ├── exception_handlers.py
│   │   └── main.py          # App factory, CORS, router registration.
│   │
│   ├── knowledge/           # Knowledge Engine.
│   │   ├── engine.py        # Orchestrator — entry point: build_knowledge()
│   │   ├── memory.py        # Adaptive goal that persists across sessions.
│   │   └── rules.py         # Pattern detection rules (deaths, CS, streaks…)
│   │
│   ├── training/            # Training Engine.
│   │   ├── engine.py        # Orchestrator — entry point: build_training()
│   │   ├── rules.py         # Skill catalog and role progression sequences.
│   │   ├── goals.py         # Skill selection from priority ranking.
│   │   ├── exercises.py     # Exercise generation with adaptive thresholds.
│   │   ├── progress.py      # Stateless exercise evaluation from match data.
│   │   ├── completion.py    # Auto-advance logic when success condition is met.
│   │   ├── planner.py       # Daily focus, weekly roadmap, history builder.
│   │   └── models.py        # Dataclasses: SkillNode, Exercise, TrainingViewModel…
│   │
│   ├── draft/               # Draft intelligence engine.
│   │
│   ├── services/            # Stateless services called by ViewModels.
│   │   ├── priority_engine.py   # Win/loss delta → ranked Priority list.
│   │   ├── champion_coach.py    # Per-champion classification and analysis.
│   │   ├── post_game_review.py  # Per-match dimension breakdown.
│   │   ├── sync_service.py      # Incremental match sync scheduling.
│   │   └── setup_service.py     # Account lookup and initial configuration.
│   │
│   ├── viewmodels/          # Orchestration layer. Each ViewModel calls engines
│   │                        # and services, then returns a dataclass that the
│   │                        # route serializes. No HTTP logic here.
│   └── config/
│       └── constants.py     # Shared domain constants.
│
├── frontend/
│   ├── electron/
│   │   ├── main.ts          # Electron main process. Window creation, IPC handlers.
│   │   └── preload.ts       # Context bridge — controlled API exposure to renderer.
│   └── src/
│       ├── features/        # Feature-based architecture. One folder per page:
│       │   ├── dashboard/   #   dashboard · coaching · matches · draft
│       │   ├── coaching/    #   progress · knowledge · training · settings
│       │   ├── matches/
│       │   ├── draft/
│       │   ├── progress/
│       │   ├── knowledge/
│       │   ├── training/
│       │   └── settings/
│       │
│       ├── components/
│       │   ├── lol/         # LoL-specific design system: LoLCard, LoLScoreRing,
│       │   │                # LoLGradeBadge, LoLSection, LoLEmptyState…
│       │   └── layout/      # Sidebar, TitleBar, layout scaffolding.
│       │
│       ├── api/
│       │   ├── client.ts    # Axios instance. Base URL from VITE_API_PORT.
│       │   └── hooks/       # Per-feature TanStack Query hooks.
│       │
│       ├── store/           # Zustand slices for global client state.
│       └── lib/             # Shared utilities (cn, formatters…)
│
├── tests/                   # pytest suite — 385 tests, all mocked.
├── lcu/
│   └── client.py            # LCU integration. Reads lockfile → HTTPS local API.
├── data/                    # SQLite DB and Riot API JSON cache. Gitignored.
│
├── scorer_v2.py             # Core scoring engine (role-aware, stat-based).
├── coaching_engine.py       # Core coaching engine (rule-based, no ML).
├── riot_api.py              # Riot Games API HTTP client with response caching.
├── parser.py                # Match JSON → internal 38-field schema.
├── db.py                    # SQLite data access. No ORM.
├── main.py                  # Streamlit entry point (legacy interface).
└── requirements.txt
```

---

## Engines

### How they interact

```
  Riot API data (raw)
        │
        ▼
  scorer_v2              ← scores each game per role
        │
        ├──▶ priority_engine     ← ranks skills by win/loss delta
        │
        ├──▶ knowledge/engine    ← memory + patterns + adaptive goal
        │
        └──▶ training/engine     ← skill tree + exercises + auto-completion
```

---

### Scorer V2 (`scorer_v2.py`)

The foundation. Every other engine consumes its output.

| | |
|---|---|
| **Input** | `list[dict]` match history + role string |
| **Output** | `ScoreResultV2` — dimensions, percentile benchmarks, trend, confidence, per-game `MatchScore` objects |
| **Key functions** | `score_match(match, reference_matches)` · `analyze_player(matches, role)` |
| **Baseline** | Player's own historical distribution — not population averages |
| **Dependencies** | None (pure computation) |

Scoring dimensions:

| Role | Dimension 1 | Dimension 2 | Dimension 3 |
|---|---|---|---|
| ADC | Economy | Positioning | Combat Impact |
| TOP | Lane Control | Pressure | Survival |

---

### Priority Engine (`backend/services/priority_engine.py`)

Answers: *"What single metric, if improved, would win the most games?"*

| | |
|---|---|
| **Input** | `list[dict]` match history + role |
| **Output** | `list[Priority]` — each with `metric_key`, `impact_score`, `evidence`, `recommendation`, win/loss averages |
| **Method** | Delta between metric value in won games vs. lost games, normalized to an impact score |
| **Dependencies** | `db.py` (match data only) |

---

### Knowledge Engine (`backend/knowledge/`)

Maintains a stateful understanding of the player across sessions.

| | |
|---|---|
| **Input** | No arguments — reads state from `db.py` internally |
| **Output** | `KnowledgeViewModel` — session summary, adaptive goal, patterns, insights, recommendations |
| **Modules** | `memory.py` (persistent adaptive goal) · `rules.py` (pattern detection) |
| **Dependencies** | `scorer_v2` · `priority_engine` · `db.py` |

---

### Training Engine (`backend/training/`)

Converts the priority ranking into a single, measurable, auto-evaluating exercise.

| | |
|---|---|
| **Input** | No arguments — reads state and match data from `db.py` internally |
| **Output** | `TrainingViewModel` — active skill, exercise, progress dots, daily plan, weekly roadmap, history |
| **State** | JSON blob in `config` table under key `training_state_v1` |
| **Completion** | 4 of the last 5 games meeting the metric condition → skill marked complete, next selected automatically |
| **Dependencies** | `scorer_v2` · `priority_engine` · `db.py` |

Skill tree progression:

| Role | Sequence |
|---|---|
| ADC | Survival → Farming → Impact → Consistency |
| TOP | Survival → Farming → Pressure → Impact → Consistency |

---

### Coaching Engine (`coaching_engine.py`)

Rule-based weekly coaching. Detects the primary problem, generates a weekly goal, and produces a structured practice plan.

| | |
|---|---|
| **Input** | `ScoreResultV2` + match history + role |
| **Output** | `CoachingResult` — problem label, weekly goal, training plan, evidence |
| **Rules** | Explicit, auditable — no ML, no LLM |
| **Dependencies** | `scorer_v2` output |

---

### Champion Coach (`backend/services/champion_coach.py`)

Per-champion analysis within the player's own match history.

| | |
|---|---|
| **Input** | Champion name + match history |
| **Output** | Classification (Main / Growth Pick / Risk Pick), strengths, weaknesses, specific objective |
| **Dependencies** | `db.py` (champion-filtered match data) |

---

### Draft Engine (`backend/draft/`)

Real-time draft intelligence during champion select.

| | |
|---|---|
| **Input** | LCU live draft state (via `lcu/client.py`) |
| **Output** | Contextual recommendations, composition analysis |
| **Transport** | WebSocket at `ws://127.0.0.1:8766/ws/draft` |
| **Dependencies** | `lcu/client.py` · `db.py` |

---

### Match Review (`backend/services/post_game_review.py`)

Full breakdown of a single game on demand.

| | |
|---|---|
| **Input** | `match_id` |
| **Output** | Per-dimension scores, metric values, strengths, weaknesses, improvement notes |
| **Endpoint** | `GET /api/v1/matches/{match_id}/review` |

---

## API Reference

All endpoints are under `/api/v1`. Interactive docs at `http://127.0.0.1:8766/docs`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System status: DB, LCU, Riot API, last sync time |
| `GET` | `/dashboard` | Player profile + recent performance summary |
| `GET` | `/matches` | Match list with scores and dimensions |
| `GET` | `/matches/{id}/review` | Full per-game breakdown |
| `GET` | `/coaching` | Active coaching recommendation |
| `GET` | `/coaching/champion` | Champion-specific analysis |
| `GET` | `/draft` | Current draft intelligence snapshot |
| `GET` | `/settings` | Player config, region, sync state |
| `GET` | `/settings/api-key/status` | API key validity, age, masked value |
| `POST` | `/settings/api-key` | Save a new API key |
| `DELETE` | `/settings/api-key` | Remove the stored API key |
| `POST` | `/settings/sync` | Trigger an incremental match sync |
| `GET` | `/progress` | Weekly goal, habits, performance trends |
| `GET` | `/knowledge` | Knowledge Engine output |
| `GET` | `/training` | Training Engine output (skill tree + active exercise) |
| `WS` | `/ws/draft` | Real-time draft state stream |

---

## Testing

```bash
pytest tests/
```

```
385 passed in 1.36s
```

All tests use mocked data — no live Riot API calls, no database writes.

| File | Coverage |
|---|---|
| `test_api.py` | All REST endpoints — request/response contracts, error cases |
| `test_viewmodels.py` | ViewModel orchestration with mocked services |
| `test_priority_engine.py` | Priority ranking correctness, edge cases |
| `test_champion_coach.py` | Champion classification rules |
| `test_matchup_intelligence.py` | Matchup analysis |
| `test_post_game_review.py` | Match review engine |
| `test_sync_service.py` | Sync scheduling, interval logic, result structure |
| `test_draft_context.py` | Draft intelligence context building |

---

## Roadmap

### Phase 1 — Scoring

- [x] ADC scoring: Economy · Positioning · Combat Impact
- [x] TOP scoring: Lane Control · Pressure · Survival
- [ ] MID scoring (architecture ready in `scorer_v2.py`)
- [ ] JUNGLE scoring
- [ ] SUPPORT scoring
- [ ] Statistical weight optimization per dimension (requires larger sample sizes)

### Phase 2 — Coaching

- [x] Rule-based coaching from win/loss patterns
- [x] Champion Coach classification (Main / Growth Pick / Risk Pick)
- [x] Knowledge Engine with persistent adaptive goal
- [ ] Matchup-specific coaching (counter-pick tendencies, lane phase patterns)

### Phase 3 — Training

- [x] Skill tree with 5 skills per role
- [x] Adaptive exercise thresholds from player percentiles
- [x] Auto-completion from post-game data (4 of 5 games)
- [ ] Champion-specific exercise variants
- [ ] Multi-week streak tracking and consistency badges

### Phase 4 — Draft

- [x] Contextual draft analysis with LCU integration
- [x] Real-time WebSocket updates during champion select
- [ ] Matchup-based counter pick suggestions
- [ ] Lane synergy scoring for duo queue

### Phase 5 — Infrastructure

- [x] Electron desktop app (Windows + macOS)
- [x] FastAPI REST + WebSocket backend
- [x] Incremental match sync
- [ ] Auto-start backend from Electron main process
- [ ] In-app API key renewal reminder before expiry
- [ ] Offline mode with cached data fallback

---

## Vision

LoL Coach is built around a single principle: **improvement should be measurable**.

Most coaching tools give you a list of things to work on. LoL Coach gives you one
thing to work on, a concrete success condition, and confirms automatically when
you have met it — then moves you to the next step.

The long-term goal is to build the most precise personal trainer for League of
Legends that can be built from public match data: not a stats dashboard, not a
chatbot, but a system that knows your game, identifies exactly where your losses
come from, and drives a structured progression that adapts as you improve.

All of that, running on your own machine.

---

## Contributing

This project is not currently open for external contributions.

---

## License

License not yet defined.
