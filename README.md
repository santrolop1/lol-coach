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
- [Build & Distribution](#build--distribution)
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
| Streamlit UI (legacy) | Stable | Full feature parity, single-process |
| Scorer V2 | Stable | ADC and TOP roles fully implemented |
| Priority Engine | Stable | Win/loss delta ranking |
| Knowledge Engine | Stable | Memory, patterns, insights, recommendations |
| Training Engine | Stable | Skill tree with auto-evaluating exercises |
| Draft Engine | Stable | LCU integration + WebSocket stream |
| Match Review | Stable | Per-game breakdown with dimension scores |
| Progress Tracking | Stable | Weekly goals, habits, trend analysis |
| Game Intelligence Platform | Stable | Champion profiles, matchup knowledge base |
| Beta Distribution (Windows) | Stable | PyInstaller + Inno Setup, no Python required |
| MID / JUNGLE / SUPPORT roles | Planned | Scorer architecture already supports them |
| Auto-start backend from Electron | Planned | Currently requires a separate terminal |
| Auto-updater | Designed | GitHub Releases strategy documented, not yet implemented |

Test suite: **385 tests passing** across 8 files.

Current version: **1.0.0-beta.1** (see `backend/version.py`)

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
| **Game Intelligence** | Deep champion and matchup knowledge base (Tryndamere + 5 matchups) |
| **About / Diagnostics** | Version info, exportable JSON diagnostic, log download, bug report links |
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
║   │  game_intelligence/                │  ║
║   └───────────────┬───────────────────┘  ║
╚═══════════════════╪══════════════════════╝
                    │
╔═══════════════════╪══════════════════════╗
║           SQLite  │  db.py                ║
║   config · player · match · analysis      ║
║   Data: %APPDATA%\LoLCoach\ (packaged)    ║
║         data/ (development)               ║
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
- All file paths go through `_paths.py` — no `Path(__file__)` outside of that module.

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
| Python | 3.11+ | Runtime |
| FastAPI | ≥ 0.110 | REST API + WebSocket server |
| uvicorn | ≥ 0.29 | ASGI server |
| Pydantic v2 | ≥ 2.6 | Schema validation |
| websockets | ≥ 12.0 | Draft real-time stream |
| requests | ≥ 2.32 | Riot API HTTP client |
| python-dotenv | ≥ 1.0 | Environment configuration |
| Streamlit | ≥ 1.35 | Legacy desktop UI (standalone, no backend needed) |
| Plotly | ≥ 5.20 | Charts in Streamlit UI |

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
| SQLite | Packaged: `%APPDATA%\LoLCoach\lol_coach.db` · Dev: `data/lol_coach.db` |
| Tables | `config`, `player`, `match` (38 columns), `analysis` |
| Migrations | Additive column additions via `PRAGMA table_info`, no data loss |
| JSON blobs | Training state and knowledge memory stored as JSON in `config` table |
| API cache | Packaged: `%LOCALAPPDATA%\LoLCoach\cache\` · Dev: `data/raw/` |

### Distribution (Windows Beta)

| Tool | Version | Role |
|---|---|---|
| PyInstaller | ≥ 6.21 | Bundles Python app + deps into a standalone .exe |
| Inno Setup | 6 | Creates `LoLCoachSetup.exe` with shortcuts and uninstaller |

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

### Para usar el instalador (beta testers)

- **Windows 10 64-bit** o superior
- **League of Legends** instalado (para Draft en tiempo real)
- **Riot Games API key** — [developer.riotgames.com](https://developer.riotgames.com/)
  - Las keys personales (gratuitas) expiran cada 24 horas.

No se requiere Python, Node.js, ni ningún otro runtime.

### Para desarrollo

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Riot Games API key** — [developer.riotgames.com](https://developer.riotgames.com/)

---

## Installation

### Opción A — Instalador (beta, sin Python)

1. Descargar `LoLCoachSetup-1.0.0-beta.1.exe` desde [Releases](https://github.com/santrolop1/lol-coach/releases)
2. Ejecutar el instalador → siguiente → instalar
3. Doble clic en el acceso directo **LoL Coach** del Escritorio
4. En la pantalla de configuración, ingresar API key, Riot ID y región
5. Clic en **Sincronizar** para descargar el historial de partidas

### Opción B — Desde el código fuente (desarrolladores)

#### 1. Clonar

```bash
git clone https://github.com/santrolop1/lol-coach.git
cd lol-coach
```

#### 2. Dependencias Python

```bash
pip install -r requirements.txt
```

#### 3. Dependencias del frontend

```bash
cd frontend
npm install
cd ..
```

#### 4. Variable de entorno del frontend

Crear `frontend/.env`:

```env
VITE_API_PORT=8766
```

---

## Running the App

### Streamlit UI (más simple — recomendado para testing)

```bash
streamlit run main.py
```

Abre automáticamente en `http://localhost:8501`. No requiere el backend FastAPI.

---

### FastAPI backend + Electron frontend

Requiere dos terminales:

**Terminal 1 — backend**

```bash
uvicorn backend.api.main:app --host 127.0.0.1 --port 8766
```

Docs interactivos: `http://127.0.0.1:8766/docs`

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

---

### Primera configuración

Ir a **Configuración**, ingresar:
- Riot Games API key (desde [developer.riotgames.com](https://developer.riotgames.com/))
- Riot ID en formato `GameName#TAG`
- Región del servidor

Luego clic en **Sincronizar** para descargar el historial.

Regiones soportadas: `LA1` · `LA2` · `NA1` · `EUW1` · `EUN1` · `BR1` · `KR` · `JP1` · `OC1`

---

## Build & Distribution

### Generar el ejecutable (Windows)

Requiere Python + dependencias instaladas:

```powershell
.\build.ps1
```

El script:
1. Limpia `dist/` y `build/` anteriores
2. Instala PyInstaller si no está instalado
3. Genera `file_version_info.txt` con la versión de `backend/version.py`
4. Ejecuta `pyinstaller LoLCoach.spec --clean --noconfirm`
5. Verifica que `dist\LoLCoach\LoLCoach.exe` existe y reporta el tamaño

Output: `dist\LoLCoach\` (~250 MB, incluye Streamlit, Plotly, Altair, FastAPI)

### Generar el instalador

Requiere [Inno Setup 6](https://jrsoftware.org/isdl.php) instalado:

```bash
iscc installer\LoLCoachSetup.iss
```

Output: `installer\LoLCoachSetup-1.0.0-beta.1.exe`

### Publicar una nueva versión

```
1. Actualizar VERSION en backend/version.py
2. .\build.ps1
3. iscc installer\LoLCoachSetup.iss
4. Crear Release en GitHub con tag vX.Y.Z
5. Adjuntar LoLCoachSetup-X.Y.Z.exe al release
```

### Cómo funciona el empaquetado

| Archivo | Rol |
|---|---|
| `_paths.py` | Resuelve rutas en dev (`data/`) y en el .exe (`%APPDATA%\LoLCoach\`) |
| `launcher.py` | Entry point del .exe — invoca `streamlit.web.cli` directamente |
| `runtime_hook.py` | Hook de PyInstaller: configura `sys.path` antes de cualquier import |
| `LoLCoach.spec` | Configuración de PyInstaller: qué incluir, qué excluir, hidden imports |
| `build.ps1` | Automatiza todo el proceso en un comando |
| `installer/LoLCoachSetup.iss` | Script Inno Setup para el instalador profesional |

Datos del usuario en la versión instalada:
- Base de datos: `%APPDATA%\LoLCoach\lol_coach.db`
- Caché de API: `%LOCALAPPDATA%\LoLCoach\cache\`
- Logs: `%APPDATA%\LoLCoach\logs\`

---

## Project Structure

```
lol-coach/
│
├── _paths.py                # Resolución de rutas — fuente de verdad para dev y PyInstaller
├── launcher.py              # Entry point del ejecutable empaquetado
├── runtime_hook.py          # Hook de PyInstaller para sys.path
├── LoLCoach.spec            # Configuración de PyInstaller
├── build.ps1                # Script de build automatizado
│
├── backend/
│   ├── version.py           # Versión canónica de la app (fuente de verdad única)
│   │
│   ├── api/
│   │   ├── routes/          # Un archivo por grupo de endpoints. Solo transporte.
│   │   ├── schemas/         # Modelos Pydantic de request y response.
│   │   ├── websocket/       # Connection manager del WebSocket de Draft.
│   │   ├── middleware/      # Middleware de logging de requests.
│   │   ├── exception_handlers.py
│   │   └── main.py          # App factory, CORS, registro de routers.
│   │
│   ├── knowledge/           # Knowledge Engine.
│   │   ├── engine.py        # Orquestador — entry point: build_knowledge()
│   │   ├── memory.py        # Objetivo adaptativo persistente entre sesiones.
│   │   └── rules.py         # Reglas de detección de patrones.
│   │
│   ├── training/            # Training Engine.
│   │   ├── engine.py        # Orquestador — entry point: build_training()
│   │   ├── rules.py         # Catálogo de skills y secuencias por rol.
│   │   ├── goals.py         # Selección de skill desde el ranking de prioridades.
│   │   ├── exercises.py     # Generación de ejercicios con umbrales adaptativos.
│   │   ├── progress.py      # Evaluación stateless de ejercicios desde match data.
│   │   ├── completion.py    # Auto-avance cuando se cumple la condición de éxito.
│   │   ├── planner.py       # Plan diario, roadmap semanal, historial.
│   │   └── models.py        # Dataclasses: SkillNode, Exercise, TrainingViewModel…
│   │
│   ├── draft/               # Motor de Draft intelligence.
│   │
│   ├── game_intelligence/   # Game Intelligence Platform.
│   │   ├── platform.py      # Facade unificado GameIntelligencePlatform.
│   │   ├── registries/      # ChampionRegistry, ItemRegistry, RuneRegistry…
│   │   ├── knowledge/
│   │   │   └── champions/
│   │   │       └── tryndamere/   # Perfil, mecánicas, builds, macro, matchups.
│   │   ├── models/          # Entidades de dominio.
│   │   └── engines/         # Motores de inteligencia por dominio.
│   │
│   ├── live_coach/          # Overlay en tiempo real durante la partida.
│   │
│   ├── services/            # Servicios stateless llamados por ViewModels.
│   │   ├── priority_engine.py
│   │   ├── champion_coach.py
│   │   ├── post_game_review.py
│   │   ├── sync_service.py
│   │   ├── setup_service.py
│   │   ├── match_resolver.py
│   │   └── matchup_repository.py
│   │
│   ├── viewmodels/          # Capa de orquestación. Cada ViewModel llama engines
│   │                        # y servicios, devuelve un dataclass que la route serializa.
│   └── config/
│       └── constants.py     # Constantes de dominio compartidas.
│
├── frontend/
│   ├── electron/
│   │   ├── main.ts          # Proceso principal de Electron. Ventana, IPC handlers.
│   │   └── preload.ts       # Context bridge — API controlada hacia el renderer.
│   └── src/
│       ├── features/        # Arquitectura por feature. Una carpeta por página.
│       ├── components/
│       │   ├── lol/         # Design system: LoLCard, LoLScoreRing, LoLSection…
│       │   └── layout/      # Sidebar, TitleBar, scaffolding.
│       ├── api/
│       │   ├── client.ts    # Instancia Axios. Base URL desde VITE_API_PORT.
│       │   └── hooks/       # Hooks TanStack Query por feature.
│       ├── store/           # Slices Zustand para estado global del cliente.
│       └── lib/             # Utilidades compartidas.
│
├── ui/                      # Páginas de la UI Streamlit (legacy).
│   ├── coaching.py
│   ├── matches.py
│   ├── draft.py
│   ├── config.py
│   ├── onboarding.py
│   └── about.py             # Pantalla beta: versión, diagnóstico, logs, reporte de bugs.
│
├── installer/
│   ├── LoLCoachSetup.iss    # Script Inno Setup para el instalador Windows.
│   └── UPDATE_DESIGN.md     # Diseño del sistema de auto-actualización (GitHub Releases).
│
├── tests/                   # Suite pytest — 385 tests.
├── lcu/
│   └── client.py            # Integración LCU. Lee lockfile → HTTPS API local.
├── data/                    # SQLite DB y caché JSON de Riot API. Gitignored.
│
├── scorer.py                # Scorer legacy (mantenido para compatibilidad con matches_vm).
├── scorer_v2.py             # Motor de scoring principal (role-aware, stat-based).
├── coaching_engine.py       # Motor de coaching (rule-based, sin ML).
├── coaching_rules.py        # Umbrales y reglas por rol.
├── riot_api.py              # Cliente HTTP Riot Games API con caché de respuestas.
├── parser.py                # Match JSON → esquema interno de 38 campos.
├── db.py                    # Acceso a datos SQLite. Sin ORM.
├── main.py                  # Entry point Streamlit (UI legacy).
├── analytics.py             # Análisis estadístico de partidas.
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
        ├──▶ priority_engine         ← ranks skills by win/loss delta
        │
        ├──▶ knowledge/engine        ← memory + patterns + adaptive goal
        │
        ├──▶ training/engine         ← skill tree + exercises + auto-completion
        │
        └──▶ game_intelligence/      ← champion profiles + matchup knowledge
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

### Game Intelligence Platform (`backend/game_intelligence/`)

Deep knowledge base of champions, matchups, wave management, macro, items, and runes.
Knowledge is data — adding a champion means creating a directory, zero engine changes.

| | |
|---|---|
| **Entry point** | `GameIntelligencePlatform` facade in `platform.py` |
| **Knowledge** | `knowledge/champions/{slug}/` — profile, mechanics, builds, macro, matchups |
| **Registries** | `ChampionRegistry`, `ItemRegistry`, `RuneRegistry` — auto-discovery via `_paths.get_knowledge_dir()` |
| **Campeones disponibles** | Tryndamere (con matchups vs. Darius, Garen, Teemo, Fiora, Malphite) |
| **Endpoint** | `GET /api/v1/champion/{champion}?role=TOP&enemy=Darius` |

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
| `GET` | `/champion/{champion}` | Game Intelligence — champion + matchup knowledge |
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

### Beta 1.0 — Distribución ✅

- [x] `_paths.py` — rutas compatibles con dev y PyInstaller
- [x] `launcher.py` — entry point del ejecutable sin Python
- [x] `LoLCoach.spec` — configuración PyInstaller completa
- [x] `build.ps1` — build automatizado en un comando
- [x] `installer/LoLCoachSetup.iss` — instalador Inno Setup con shortcuts y uninstaller
- [x] `backend/version.py` — versión canónica única
- [x] `ui/about.py` — pantalla de diagnóstico para beta testers
- [x] Rutas hardcodeadas eliminadas de `setup_service`, `match_resolver`, `ui/draft`, `matchup_repository`, `champion_registry`
- [x] Datos del usuario en `%APPDATA%\LoLCoach\` (instalado) o `data/` (dev)
- [ ] Firmar el ejecutable con certificado de código (post-beta)
- [ ] Auto-updater via GitHub Releases (diseñado en `installer/UPDATE_DESIGN.md`)

### Phase 1 — Scoring

- [x] ADC scoring: Economy · Positioning · Combat Impact
- [x] TOP scoring: Lane Control · Pressure · Survival
- [ ] MID scoring (architecture ready in `scorer_v2.py`)
- [ ] JUNGLE scoring
- [ ] SUPPORT scoring

### Phase 2 — Coaching

- [x] Rule-based coaching from win/loss patterns
- [x] Champion Coach classification (Main / Growth Pick / Risk Pick)
- [x] Knowledge Engine with persistent adaptive goal
- [ ] Matchup-specific coaching

### Phase 3 — Training

- [x] Skill tree with 5 skills per role
- [x] Adaptive exercise thresholds from player percentiles
- [x] Auto-completion from post-game data (4 of 5 games)
- [ ] Champion-specific exercise variants

### Phase 4 — Draft

- [x] Contextual draft analysis with LCU integration
- [x] Real-time WebSocket updates during champion select
- [ ] Matchup-based counter pick suggestions

### Phase 5 — Game Intelligence

- [x] Champion profiles (Tryndamere)
- [x] Matchup knowledge base (5 matchups)
- [ ] Wave management engine
- [ ] Item build intelligence
- [ ] Additional champion profiles

### Phase 6 — Infrastructure

- [x] Electron desktop app (Windows + macOS)
- [x] FastAPI REST + WebSocket backend
- [x] Incremental match sync
- [x] Windows installer (PyInstaller + Inno Setup)
- [ ] Auto-start backend from Electron main process
- [ ] Auto-updater (GitHub Releases)
- [ ] macOS packaging

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
