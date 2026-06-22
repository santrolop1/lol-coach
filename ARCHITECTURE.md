# ARCHITECTURE.md — Arquitectura técnica de LoL Coach

---

## Visión general

```
Riot API
    │
    ▼
riot_api.py ──► data/raw/*.json
    │
    ▼
parser.py (MatchData, 38 campos)
    │
    ▼
db.py (SQLite — tabla match, V1 + V2)
    │
    ├──► scorer_v2.py (ScoreResultV2) ──► coaching_engine.py (CoachingResult)
    │
    └──► scorer.py (legado V1) ──► recommendations.py (legado)
                                         │
                                         ▼
                                      ui/ (Streamlit)
```

---

## Capa de datos — db.py

### Tabla `match`
Columnas V1 (12): match_id, puuid, champion, role, result, kills, deaths, assists, cs, damage, duration_sec, played_at.

Columnas V2 (26 añadidas en Sprint 1):
- Economía: gold_earned
- Visión: vision_score, wards_placed, wards_killed, control_wards_placed, control_wards_bought
- Daño: damage_to_objectives, damage_to_turrets, damage_taken, damage_self_mitigated
- Utilidad: heals_on_teammates, time_ccing_others, turret_takedowns, turret_plates_taken
- Supervivencia: time_spent_dead, longest_time_alive
- Challenges (Riot): kill_participation, team_damage_pct, cs_at_10, max_cs_advantage
- Objetivos: baron_kills, dragon_kills, objectives_stolen, enemy_jungle_cs
- Flags: game_ended_surrender, first_blood

Migración: `PRAGMA table_info(match)` detecta columnas existentes antes de `ALTER TABLE ADD COLUMN`. Compatible con todas las versiones de SQLite.

### Tabla `config`: key-value store (puuid, api_key, etc.)
### Tabla `player`: perfil del jugador (riot_id, tag, rank, lp, etc.)
### Tabla `analysis`: resultados de scoring V1 (legado, ya no se usa activamente)

---

## Capa de parsing — parser.py

Convierte un objeto `participants[]` de la Riot Match-V5 API en un dataclass `MatchData` con 38 campos. Los campos del objeto `challenges` se extraen defensivamente con `.get("challenges", {}) or {}` para evitar errores en partidas pre-patch 12.x donde el objeto puede ser null.

Método `to_v2_fields()`: devuelve solo los campos V2 no-nulos, listo para `db.update_match_v2()`.

---

## Capa de scoring — scorer_v2.py

### Principio de diseño
Scores son **auto-relativos**: el percentile rank del jugador dentro de su propio historial. No hay benchmarks externos inventados.

Score = fracción de partidas propias donde el valor es ≤ valor actual × 100.
- Score 50 = rendimiento mediano para ese jugador.
- Score 75 = mejor que el 75% de sus propias partidas.

### Scoring no-paramétrico (percentile rank)
No asume ninguna forma de distribución. Robusto ante outliers y partidas cortas.

### Normalización por duración
Métricas de volumen (gold, daño, objetivos) se normalizan por minutos de juego. Esto hace comparables las partidas de distinta duración y las partidas rendidas.

### Dimensiones por rol

**ADC:**
- Economy: cs_per_min, cs_at_10, gold_per_min
- Positioning: deaths (inverso), time_dead_pct (inverso), longest_alive_pct
- Combat Impact: kill_participation, team_damage_pct, objectives_per_min

**TOP:**
- Lane Control: cs_at_10, max_cs_advantage, gold_per_min
- Pressure: turrets_per_min, turret_takedowns, objectives_per_min
- Survival: deaths (inverso), time_dead_pct (inverso)

### Pesos
Iguales entre métricas de cada dimensión. Con N<50 por rol, el error estándar de pesos estadísticos supera el 30%. Se revisarán cuando N≥50.

### Análisis temporal
- **Tendencia**: regresión lineal OLS cerrada sobre overall_scores ordenados por played_at. Umbral: ±1.5 pts/partida (en 10 partidas = ±15 pts, perceptible).
- **Consistencia**: Coefficient of Variation (CV = std/|mean| × 100). Consistency = max(0, 100 − CV).

### Niveles de confianza
- N < 5: insufficient
- N 5-9: preliminary
- N 10-19: reliable
- N ≥ 20: robust

### Dataclasses de salida
- `DimensionScore`: score, métricas crudas, notas
- `MatchScore`: scores por partida individual
- `MetricStats`: n, mean, std, p25, p50, p75, p90
- `PlayerBenchmarks`: percentiles calculados desde datos reales
- `ScoreResultV2`: análisis completo (dimensions, overall, trend, consistency, confidence, benchmarks, limitations)

---

## Capa de coaching — coaching_engine.py + coaching_rules.py

### Separación de responsabilidades
- `coaching_rules.py`: Solo datos. Textos, umbrales documentados con su fuente, planes de acción. Sin funciones.
- `coaching_engine.py`: Solo lógica. Evaluación de condiciones, generación de evidencia, selección de problema principal.

### Tipos de umbrales
1. **research**: Evidencia de coaching profesional / Arquitectura V2 (absolutos, no del dataset local).
   - ADC: deaths ≤6, KP ≥50%, cs_at_10 ≥55
   - TOP: deaths ≤5, cs_at_10 ≥60
2. **data**: Percentiles del historial propio del jugador (relativos).
3. **hybrid**: Umbral absoluto validado con datos locales.

### Flujo de analyze_coaching()
1. Filtrar partidas por rol y ordenar cronológicamente.
2. Detectar tilt/racha (si most_recent=LOSS y 4+ en mismo día → TILT ACTIVO con severity=90).
3. Evaluar todos los patrones del rol.
4. Seleccionar primary_problem por mayor severidad.
5. Generar evidencia con números reales (WIN avg vs LOSS avg, P25/P50/P75).
6. Derivar weekly_goal desde datos (target = WIN average, o P75 propio).
7. Obtener training_plan desde coaching_rules.py.
8. Detectar fortalezas desde victorias vs derrotas.
9. Construir CoachingResult.

### Dataclasses de salida
- `WeeklyGoal`: description, metric, current, target, window
- `TrainingPlan`: primary, secondary (2 acciones)
- `Strength`: name, evidence
- `CoachingResult`: primary_problem, evidence, probable_cause, impact, weekly_goal, training_plan, strengths, improvements, trend_summary, confidence_level, session_warning

---

## Fases de la Arquitectura V2 (documento original)

El sistema fue diseñado en 6 fases. Estado actual:

| Fase | Nombre | Estado |
|------|--------|--------|
| 1 | Player Coaching (ADC/TOP) | Parcial (score + coaching, sin UI) |
| 2 | Role Engine (MID/JGL/SUP) | Pendiente |
| 3 | Coaching Engine expandido | En progreso (V1 completado) |
| 4 | Progress Tracking | Pendiente |
| 5 | Benchmarks externos | Pendiente |
| 6 | Team Coaching | Pendiente |

---

## Quirks y limitaciones conocidas

- `summoner_*.json` en data/raw/ es un perfil de invocador, no una partida. El script de reparseo lo descarta correctamente.
- `team_damage_pct` no discrimina win/loss en este dataset (delta=-0.001). Se mantiene con peso igual por evidencia externa.
- `cs_at_10` está invertido en este dataset (WIN avg < LOSS avg). Posible sesgo de muestra pequeña.
- `game_ended_surrender=1`: incluido en análisis pero marcado. Las métricas de duración (gold/min, etc.) siguen siendo comparables por normalización.
- Windows: usar `python -X utf8` para evitar UnicodeEncodeError en terminales con encoding cp1252.
