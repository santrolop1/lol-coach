# PROJECT_STATE.md — Estado actual del proyecto LoL Coach

Última actualización: 2026-06-22

---

## ¿Qué es este proyecto?

LoL Coach es una aplicación de coaching personal para League of Legends.
Analiza el historial de partidas del jugador (vía Riot API) y genera
diagnósticos de coaching basados en reglas y datos reales. Sin IA, sin LLM.

---

## Estado de los sprints

### Sprint 1 — Expansión de datos (COMPLETADO)
- Se añadieron 26 columnas V2 a la tabla `match` en SQLite.
- Migración segura con `PRAGMA table_info` (compatible con todas las versiones de SQLite).
- Se reparsaron los JSONs de `data/raw/` sin llamar a la API de Riot.
- 30/30 partidas actualizadas. Cobertura promedio: 25.9/26 campos V2.

### Sprint 2.1 — Scoring Engine V2 (COMPLETADO)
- Creado `scorer_v2.py` con scoring por rol basado en percentil propio.
- ADC: Economy / Positioning / Combat Impact.
- TOP: Lane Control / Pressure / Survival.
- Análisis de tendencia (regresión OLS), consistencia (CV), confidence level.

### Sprint 3 — Coaching Engine V1 (COMPLETADO)
- Creados `coaching_engine.py` y `coaching_rules.py`.
- 6 patrones ADC: tilt, exceso de muertes, baja KP, CS deficiente, bajos objetivos, inconsistencia.
- 5 patrones TOP: tilt, exceso de muertes, mala fase de líneas, baja presión, baja conversión de ventaja, inconsistencia.
- Evidencia con números reales. Objetivo semanal derivado de datos. Sin ML.

### Sprint 3.1 — Corrección de hallazgos críticos (COMPLETADO)
- LOW_OBJECTIVE_CONTRIBUTION: implementado en `_evaluate_adc_problems()` (antes era código muerto).
- LOW_ADVANTAGE_CONVERSION (TOP): implementado en `coaching_rules.py` + `_evaluate_top_problems()`.
- Tilt con decaimiento temporal: severity=85 (<12h), 50 (12-24h), 15 (24-48h), 5 (>48h). Ya no bloquea permanentemente.
- Duplicación de tilt eliminada: `_count_consecutive_losses()` es la única fuente de verdad.
- Win rate añadido al `trend_summary` para N≥10.
- Strengths ya no usan outliers: requieren ≥3 victorias sobre el P75 personal.
- LOW_CS_AT_10 severity reducida al 40% cuando la correlación local está invertida.

---

## Estado de los datos (2026-06-22)

| Rol | N partidas | Confidence | Nota |
|-----|-----------|------------|------|
| ADC | 28        | ROBUST     | Datos suficientes para coaching |
| TOP | 1         | INSUFFICIENT | Necesita ≥5 para activar coaching |

### Hallazgos clave del dataset ADC
- **Deaths discrimina win/loss más que ninguna otra métrica**: WIN avg=5.75, LOSS avg=7.82 (delta=2.07)
- **Kill participation**: WIN avg=0.475, LOSS avg=0.407 (delta=0.068)
- **CS@10 está INVERTIDO** en este dataset: WIN avg=43.7 < LOSS avg=47.5. Posible sesgo de muestra.
- **Tilt detectado**: 7 derrotas consecutivas (6 el mismo día, 2026-06-20). Primary problem actual.
- **Overall score ADC**: 52.4 (auto-relativo, P52 de historial propio). Consistencia: 67.1/100.
- **2 partidas rendidas** (game_ended_surrender=1) incluidas en análisis.

---

## Archivos del proyecto

### Datos y configuración
- `data/lol_coach.db` — SQLite con las partidas (schema V1 + V2)
- `data/raw/*.json` — JSONs crudos de la Riot API
- `.env` o config en DB — API key de Riot

### Núcleo del sistema
- `db.py` — Capa de acceso a datos. Migración V2 automática.
- `parser.py` — Convierte JSON de Riot API a MatchData (38 campos).
- `riot_api.py` — Llamadas a la API de Riot.
- `main.py` — Entry point de la aplicación.

### Sistema de scoring (Sprint 2)
- `scorer_v2.py` — Motor de scoring profesional por rol. API pública: `analyze_player()`, `score_match()`, `calculate_benchmarks()`.
- `scorer.py` — Motor de scoring V1 (legado, no modificar).

### Sistema de coaching (Sprint 3)
- `coaching_engine.py` — Lógica de evaluación de reglas. API pública: `analyze_coaching()`.
- `coaching_rules.py` — Solo datos: textos, umbrales, fuentes. Sin lógica.

### Sistema de recomendaciones (legado)
- `recommendations.py` — Sistema V1 simple. No modificar. Será reemplazado por coaching engine en el futuro.

### UI
- `ui/` — Interfaz Streamlit. No modificar hasta que se planifique Sprint 4 (integración de coaching en UI).
- `ui/config.py`, `ui/matches.py`, `ui/analysis.py`

### Scripts de utilidad
- `scripts/reparse_raw.py` — Reparsea JSONs de data/raw/ sin llamar a la API.
- `scripts/validate_v2.py` — Valida completitud de campos V2 en SQLite.
- `scripts/test_scorer_v2.py` — Test del scorer con datos reales.
- `scripts/test_coaching.py` — Test del coaching engine con datos reales.

---

## Lo que NO está implementado

- Coaching para MID, JUNGLE, SUPPORT.
- Análisis de Champion Select o Meta.
- Integración del coaching engine en la UI de Streamlit.
- Benchmarks externos (comparación con jugadores del mismo elo).
- Progress tracking entre sesiones.
- Team Coaching.
- Guardar resultados de coaching en la DB.

---

## Para ejecutar tests

```
python scripts/test_scorer_v2.py
python scripts/test_coaching.py
python scripts/validate_v2.py
```
