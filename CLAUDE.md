# LoL Coach — CLAUDE.md

Guía de referencia para Claude Code. Leer antes de tocar cualquier archivo.

---

## Qué es este proyecto

Aplicación de escritorio (Electron 33 + electron-vite) para entrenar en League of Legends.
Analiza el historial de partidas del jugador y genera recomendaciones personalizadas.

**Stack:**
- **Frontend:** Electron 33, React 18, TypeScript, TanStack Query v5, Framer Motion, Tailwind CSS
- **Backend:** FastAPI en puerto **8766**, SQLite via `db.py`
- **UI legacy:** Streamlit (`streamlit run main.py`) — sigue en uso, no romper

---

## Cómo correr el proyecto

```bash
# Backend FastAPI
uvicorn backend.api.main:app --host 127.0.0.1 --port 8766 --reload

# Frontend Electron (en /frontend)
npm run dev

# UI Streamlit (legacy)
streamlit run main.py
```

---

## Reglas absolutas

1. **No hacer git commit ni git push automáticamente.** Siempre esperar aprobación del usuario.
2. **No exponer la Riot API key.** Mask: `RGAPI-${'*'.repeat(20)}${key.slice(-4)}`
3. **No usar IA generativa** dentro de los engines del backend.
4. **No duplicar cálculos** — toda la lógica vive en el backend; el frontend solo renderiza.
5. **No mover lógica al frontend.**
6. **No cambiar la lógica del programa ni romper compatibilidad** sin autorización explícita.
7. **No agregar nuevas funcionalidades** sin que el usuario las pida.
8. **No añadir comentarios** que expliquen qué hace el código — solo el POR QUÉ cuando no es obvio.

---

## Arquitectura actual

```
lol-coach/
│
├── main.py                    ← Entry point Streamlit (legacy UI)
├── db.py                      ← SQLite: config, player, match, analysis
├── scorer_v2.py               ← Motor de scoring por rol (NO TOCAR)
├── coaching_engine.py         ← Motor de coaching (NO TOCAR)
├── coaching_rules.py          ← Umbrales por rol
│
├── backend/
│   ├── api/
│   │   ├── main.py            ← FastAPI app (puerto 8766)
│   │   ├── routes/            ← Endpoints puros — sin lógica de negocio
│   │   ├── schemas/           ← Pydantic v2 schemas
│   │   ├── middleware/
│   │   └── websocket/
│   │
│   ├── config/
│   │   └── constants.py       ← Constantes compartidas entre módulos
│   │
│   ├── services/
│   │   ├── priority_engine.py ← compute_priorities(matches, role) → list[Priority]
│   │   ├── champion_coach.py  ← analyze_champion(champion, role, scored) → ChampionCoachResult
│   │   ├── matchup_analyzer.py← analyze_matchups(matches, role) → MatchupResult
│   │   ├── post_game_review.py← generate_review(match, history, ...) → PostGameReview
│   │   ├── sync_service.py    ← Sincronización incremental automática
│   │   └── [otros servicios]
│   │
│   ├── knowledge/
│   │   ├── engine.py          ← build_knowledge() → KnowledgeViewModel
│   │   ├── memory.py          ← Objetivos adaptativos en config table
│   │   └── rules.py           ← Detección de patrones conductuales
│   │
│   ├── training/
│   │   ├── engine.py          ← build_training() → TrainingViewModel
│   │   ├── rules.py           ← SKILL_CATALOG, ROLE_PROGRESSION
│   │   ├── exercises.py       ← generate_exercise() con umbrales p25/p75
│   │   ├── goals.py           ← select_skill(), build_skill_tree()
│   │   ├── progress.py        ← evaluate_exercise()
│   │   └── completion.py      ← is_complete(), complete_and_advance()
│   │
│   ├── draft/                 ← LCU + draft intelligence
│   └── viewmodels/            ← Orquestación — cero cálculos en el frontend
│
├── frontend/
│   └── src/
│       ├── api/
│       │   └── client.ts      ← apiClient (axios, baseURL = http://127.0.0.1:8766/api/v1)
│       ├── features/
│       │   ├── coaching/      ← useCoaching hook + CoachingPage
│       │   ├── draft/         ← useDraft hook (polling 3s) + DraftPage
│       │   ├── training/      ← useTraining hook + TrainingPage
│       │   ├── knowledge/     ← useKnowledge hook + KnowledgePage
│       │   ├── matches/       ← useMatches, useMatchReview hooks
│       │   ├── progress/      ← useProgress hook
│       │   └── dashboard/     ← useDashboard hook
│       └── components/
│           └── lol/           ← Design system: LoLCard, LoLScoreRing, LoLSection,
│                                 LoLPriorityCard, LoLMetricCard, LoLHeroCard,
│                                 LoLEmptyState, LoLErrorState, LoLScoreBadge
│
├── ui/                        ← Páginas Streamlit legacy (no tocar la lógica)
└── tests/                     ← pytest
```

---

## APIs de los motores core

### scorer_v2
```python
score_match(match: dict, reference_matches: list[dict]) → MatchScore | None
analyze_player(matches: list[dict], role: str) → ScoreResultV2
# ScoreResultV2: overall_score, dimensions (dict), trend, consistency_score,
#                confidence_level, match_scores, benchmarks (PlayerBenchmarks)
# PlayerBenchmarks.metrics: dict[str, MetricStats]
# MetricStats: n, mean, std, p25, p50, p75, p90
# Dimensiones ADC: Economy, Positioning, Combat Impact
# Dimensiones TOP: Lane Control, Pressure, Survival
```

### coaching_engine
```python
analyze_coaching(score_result: ScoreResultV2, match_history: list[dict], role: str) → CoachingResult
# CoachingResult: primary_problem, evidence, probable_cause, impact,
#                 weekly_goal (WeeklyGoal), training_plan (TrainingPlan),
#                 strengths, improvements, trend_summary, confidence_level,
#                 sample_size, session_warning
# WeeklyGoal.window es str (ej: "proximas 10 partidas") — NO int
```

### priority_engine
```python
compute_priorities(matches: list[dict], role: str) → list[Priority]
# Priority: title, metric_key, impact_score (1-20), confidence, evidence,
#           recommendation, current_value, target_value, unit,
#           win_avg, loss_avg, n_wins, n_losses
# Máximo 5 prioridades; requiere mín 3 wins Y 3 losses
```

### training engine
```python
build_training() → TrainingViewModel
# Estado persistido en config table: "training_state_v1" (JSON)
# Evaluación: 4/5 partidas exitosas → drill completado (auto-completion)
```

---

## Base de datos (SQLite via db.py)

**Tablas:**
- `config` — clave/valor JSON (`get_config(key)`, `save_config(key, value)`)
- `player` — perfil del jugador (puuid, riot_id, tag, level, rank, tier, lp)
- `match` — 38+ columnas; V1 base + V2 con gold_earned, vision_score, cs_at_10, etc.
- `analysis` — scores calculados por partida

**Regla:** No añadir tablas nuevas. Usar `config` con claves con prefijo para estado nuevo.
Prefijo usado por Game Intelligence Platform: `gi_`

---

## Frontend — reglas de hooks

- **SIEMPRE usar `apiClient`** (axios configurado). NUNCA `fetch()` directamente — en Electron los URLs relativos no llegan al backend.
- `apiClient` tiene `baseURL = http://127.0.0.1:${PORT}/api/v1` (PORT default 8766)
- TanStack Query v5: `useQuery({ queryKey, queryFn, staleTime, refetchInterval })`
- Polling draft: `refetchInterval: 3_000` (el draft cambia rápido)
- Polling coaching: `refetchInterval: 3 * 60_000`

---

## Endpoints actuales (NO modificar contratos)

```
GET /api/v1/health
GET /api/v1/coaching          ?role=ADC|TOP &limit=20
GET /api/v1/coaching/champion ?champion=Tryndamere &role=TOP
GET /api/v1/training
GET /api/v1/progress
GET /api/v1/knowledge
GET /api/v1/matches           ?role= &limit=
GET /api/v1/matches/{id}/review
GET /api/v1/dashboard
GET /api/v1/draft
GET /api/v1/settings
POST /api/v1/settings
WS  /ws/draft
```

---

## Próximo módulo: Game Intelligence Platform

Módulo nuevo en `backend/game_intelligence/`. **No toca nada existente.**

Arquitectura aprobada (Sprint E-X.1). Estructura principal:

```
backend/game_intelligence/
  platform.py              ← GameIntelligencePlatform facade
  models/                  ← Entidades de dominio (champion, matchup, wave, macro, item, rune…)
  registries/              ← APIs internas: ChampionRegistry, MatchupRegistry, WaveRegistry…
                              KnowledgeAPI (facade unificado)
  knowledge/
    champions/             ← Un directorio por campeón (auto-descubierto)
      tryndamere/
        profile.py         ← PROFILE: ChampionProfile
        mechanics.py
        builds.py
        macro.py
        matchups/
          darius.py        ← MATCHUP: MatchupProfile
    wave/                  ← Técnicas universales (freeze, slow_push, etc.)
    macro/                 ← Patrones macro universales
    items/                 ← Base de conocimiento de items
    runes/                 ← Páginas de runas
    objectives/
    vision/
    patches/
  engines/                 ← 13 motores de inteligencia
    champion/              ← ChampionIntelligenceEngine
    matchup/               ← MatchupIntelligenceEngine
    macro/                 ← MacroIntelligenceEngine
    wave/                  ← WaveIntelligenceEngine
    item/                  ← ItemIntelligenceEngine
    rune/                  ← RuneIntelligenceEngine
    objective/             ← ObjectiveIntelligenceEngine
    vision/                ← VisionIntelligenceEngine
    patch/                 ← PatchIntelligenceEngine
    learning/              ← LearningIntelligenceEngine
    review/                ← ReviewIntelligenceEngine
    training/              ← TrainingIntelligenceEngine
    coach/                 ← CoachIntelligenceEngine (explainer adaptativo)
  viewmodels/              ← ChampionIntelligenceViewModel, etc.
```

**Regla de oro de la Platform:**
- Nunca `if champion == "X"` en ningún motor.
- Nunca leer archivos directamente desde motores — todo pasa por `KnowledgeAPI`.
- Agregar un campeón = crear directorio en `knowledge/champions/`. Cero cambios al motor.

**Nuevo endpoint:** `GET /api/v1/champion/{champion}?role=TOP&enemy=Darius`

**Persistencia:** tabla `config` con claves `gi_learning_{champion}_{role}_v1` y `gi_active_drill_{champion}_{role}_v1`

**Fases de implementación:**
1. Fundamentos (models, registries, knowledge/wave, knowledge/macro, platform.py)
2. Primer perfil (tryndamere + 5 matchups) + ChampionIntelligenceEngine
3. Learning IE + Training IE (drills por campeón)
4. Review IE + Coach IE
5. API + UI React
6. Motores adicionales (Wave IE, Macro IE, Item IE…)
7. Patch IE + expansión de perfiles

---

## Seguridad de API key

```python
# Python
masked = f"RGAPI-{'*' * 20}{key[-4:]}"

# TypeScript
masked = `RGAPI-${'*'.repeat(20)}${key.slice(-4)}`
```

Nunca loguear la key completa. Nunca incluirla en respuestas de API.

---

## Constantes clave

```python
# backend/config/constants.py
MIN_GAMES_TABLE    = 2
MIN_GAMES_QUALIFY  = 3
MIN_GAMES_RELIABLE = 10
MIN_GAMES_ROBUST   = 20
MIN_MATCHUP_GAMES  = 3
ROBUST_MATCHUP_GAMES = 8
MIN_CHAMPION_GAMES = 5
ROBUST_CHAMPION_GAMES = 10
```

---

## Tests

```bash
pytest tests/
```

Archivos: `test_api.py`, `test_champion_coach.py`, `test_matchup_intelligence.py`,
`test_post_game_review.py`, `test_priority_engine.py`, `test_sync_service.py`, `test_viewmodels.py`

**Regla tests:** `WeeklyGoal.window` es `str`, no `int`. No usar mocks de DB — los tests deben usar SQLite real.
