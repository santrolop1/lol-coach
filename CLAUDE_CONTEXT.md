# CLAUDE_CONTEXT.md — Contexto de onboarding para nuevas conversaciones

Leer este archivo primero. Luego PROJECT_STATE.md → ARCHITECTURE.md → DECISIONS.md → ROADMAP.md.

---

## ¿Qué es este proyecto?

Aplicación local de coaching personal para League of Legends.
Analiza partidas del jugador vía Riot API y genera diagnósticos basados en reglas deterministas.
Sin IA, sin LLM, sin ML.

Stack: Python 3.11+, SQLite, Streamlit.
Plataforma: Windows 11. Usar `python -X utf8` en scripts para evitar UnicodeEncodeError en terminales cp1252.

---

## Estado del código (2026-06-22)

Sprints 1, 2.1 y 3 completados. Los archivos de estos sprints NO deben modificarse sin autorización explícita.

| Archivo | Sprint | Estado | Modificable |
|---------|--------|--------|-------------|
| `db.py` | 1 | Completado | Solo si se añaden columnas V3 |
| `parser.py` | 1 | Completado | Solo si Riot API cambia |
| `scorer_v2.py` | 2.1 | Completado | Solo para añadir roles |
| `coaching_engine.py` | 3 | Completado | Para añadir roles o patrones |
| `coaching_rules.py` | 3 | Completado | Para añadir textos/umbrales |
| `scorer.py` | Legado | NO MODIFICAR | Bloqueado por restricción explícita |
| `recommendations.py` | Legado | NO MODIFICAR | Bloqueado por restricción explícita |
| `ui/` | Legado | NO MODIFICAR | Hasta que Sprint 4 sea planificado |

---

## Restricciones establecidas por el usuario (RESPETAR SIEMPRE)

1. **NO modificar** `scorer.py`, `recommendations.py`, ni nada en `ui/`.
2. **NO implementar** MID, JUNGLE, SUPPORT hasta que haya N≥10 partidas de cada rol.
3. **NO implementar** Champion Select ni análisis de Meta.
4. **NO usar IA, LLM ni ML** en el coaching engine. Solo reglas y datos reales.
5. **NO inventar benchmarks** sin fuente documentada. Toda métrica comparativa debe tener fuente "research" (Arquitectura V2) o "data" (historial propio del jugador).
6. **Un solo weekly_goal** por CoachingResult.
7. **Máximo 3 strengths** por CoachingResult, basadas en datos.

---

## Cómo funciona el flujo de datos

```
db.get_matches(puuid, limit=200)
    │
    ▼
scorer_v2.analyze_player(all_matches, role="ADC")  →  ScoreResultV2
    │
    ▼
coaching_engine.analyze_coaching(score_result, all_matches, role="ADC")  →  CoachingResult
```

Los dos objetos clave son `ScoreResultV2` (de `scorer_v2.py`) y `CoachingResult` (de `coaching_engine.py`).

---

## Datos del jugador actual

- PUUID real configurado en SQLite.
- Partidas ADC: N=28, confidence=ROBUST.
- Partidas TOP: N=1, confidence=INSUFFICIENT.
- Partidas totales en DB: ~30.
- JSONs crudos: `data/raw/` (~31 archivos, 1 es un perfil de invocador no-partida).

### Hallazgo clave del dataset ADC
El diferenciador principal entre victorias y derrotas es el número de muertes:
- Victorias: avg deaths = 5.75
- Derrotas:  avg deaths = 7.82
- Delta: 2.07 muertes más en derrotas

El tilt session de 2026-06-20 (7 derrotas consecutivas, 6 en el mismo día) es el diagnóstico principal del coaching en este momento.

### Anomalía conocida
CS@10 está INVERTIDO en este dataset: WIN avg=43.7 < LOSS avg=47.5. Posible sesgo de muestra pequeña (N=28). La regla de cs_at_10 en el coaching se mantiene por evidencia externa pero con nota explícita de baja confianza local.

---

## Cómo testear

```bash
python -X utf8 scripts/test_scoring.py        # Score V2
python -X utf8 scripts/test_coaching.py       # Coaching Engine
python -X utf8 scripts/validate_v2.py         # Completitud de datos V2
python -X utf8 scripts/reparse_raw.py         # Reparsear JSONs locales (no llama a API)
```

---

## Próxima tarea más probable

**Sprint 4: Integración del coaching engine en la UI de Streamlit.**

Antes de empezar, leer:
1. `ui/analysis.py` para entender la UI actual.
2. `ROADMAP.md` sección Sprint 4 para las restricciones.

El usuario querrá ver el CoachingResult en Streamlit. El plan no modifica la lógica existente — añade una nueva pestaña "Coaching".

---

## Patrones de código establecidos a seguir

- Docstrings: una línea de resumen + sección de Args/Returns cuando el función es pública.
- Comentarios: solo cuando el WHY no es obvio. No comentar el QUÉ.
- Sin feature flags ni backwards-compat shims.
- Dataclasses para estructuras de salida (no dicts).
- Funciones privadas: prefijo `_`. API pública sin prefijo.
- Los umbrales siempre llevan su fuente documentada (research / data / hybrid).
- Los tests se ejecutan con datos reales de SQLite, no mocks.

---

## Qué NO está implementado (para no inventarlo)

- Coaching para MID, JUNGLE, SUPPORT.
- Análisis de Champion Select.
- Análisis de Meta (patches).
- Progress Tracking (comparar semanas).
- Benchmarks externos de elo.
- Team Coaching.
- Guardar CoachingResult en la DB (se calcula al vuelo).

---

## Documentos de referencia en este directorio

- `PROJECT_STATE.md` — Estado actual, archivos, datos.
- `ARCHITECTURE.md` — Diseño técnico, flujo, dataclasses.
- `ROADMAP.md` — Sprints completados y pendientes.
- `DECISIONS.md` — 12 decisiones técnicas con justificación.
- `CLAUDE_CONTEXT.md` — Este archivo. Leer primero.
