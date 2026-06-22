# ROADMAP.md — Plan de desarrollo de LoL Coach

---

## Sprints completados

### Sprint 1 — Expansión de captura de datos
Resultado: 26 nuevas columnas en SQLite. Reparseo de JSONs locales. Script de validación.
Archivos: `db.py` (reescrito), `parser.py` (reescrito), `scripts/reparse_raw.py`, `scripts/validate_v2.py`.

### Sprint 2.1 — Scoring Engine V2
Resultado: `scorer_v2.py` con scoring percentil auto-relativo por rol (ADC/TOP). Tendencia OLS, consistencia CV, confidence levels.
Archivos: `scorer_v2.py`, `scripts/test_scorer_v2.py`.

### Sprint 3 — Coaching Engine V1
Resultado: `coaching_engine.py` + `coaching_rules.py`. Diagnóstico basado en reglas, evidencia con números reales, objetivo semanal derivado de datos, plan de entrenamiento.
Archivos: `coaching_engine.py`, `coaching_rules.py`, `scripts/test_coaching.py`.

---

## Sprints pendientes — Prioridad alta

### Sprint 4 — Integración de coaching en UI
Objetivo: Mostrar CoachingResult en la UI de Streamlit.

Restricciones importantes:
- NO modificar la lógica de `ui/analysis.py` hasta planificar el cambio.
- La UI actual usa `scorer.py` (V1) y `recommendations.py`. Decidir si reemplazar o coexistir.
- Mantener compatibilidad con el flujo actual mientras se añade el tab de coaching.

Entregables esperados:
- Nueva pestaña "Coaching" en Streamlit con el diagnóstico completo.
- Visualización del objetivo semanal y plan de entrenamiento.
- Indicador visual de tilt / racha de derrotas.
- Gráfico de tendencia (overall score en el tiempo).

### Sprint 5 — Role Engine V2: MID, JUNGLE, SUPPORT
Objetivo: Añadir dimensiones y reglas para los 3 roles restantes.

Dimensiones propuestas:
- MID: Roaming Impact / Economy / Combat
- JUNGLE: Objective Control / Farm Efficiency / Gank Impact
- SUPPORT: Vision Control / Engage/Disengage / Team Utility

Restricciones:
- NO implementar hasta tener N≥10 partidas de cada rol para pruebas.
- Mismo patrón que ADC/TOP: sin benchmarks externos inventados.
- Añadir a scorer_v2.py y coaching_engine.py siguiendo el patrón existente.

---

## Sprints pendientes — Prioridad media

### Sprint 6 — Progress Tracking
Objetivo: Comparar el estado actual del jugador con su estado de hace N partidas.

Entregables:
- Guardar CoachingResult en la DB (nueva tabla `coaching_history`).
- Detectar si el weekly_goal de la semana anterior fue alcanzado.
- Mostrar "Antes / Ahora" para cada dimensión.
- Alerta de regresión: si un área mejorada vuelve a empeorar.

### Sprint 7 — Benchmarks externos
Objetivo: Comparar al jugador con jugadores reales del mismo elo.

Desafío técnico: la Riot API pública no provee percentiles por elo para la mayoría de métricas.
Opciones a evaluar:
1. Usar `/lol/challenges/v1/challenges/{id}/percentiles` (limitado a challenges).
2. Construir dataset propio descargando partidas de jugadores del mismo elo.
3. Usar datasets públicos de Kaggle/OP.GG para Gold/Plat.

Impacto: cambia el significado del score de "relativo a sí mismo" a "relativo al elo".

---

## Sprints pendientes — Prioridad baja

### Sprint 8 — Team Coaching
Objetivo: Analizar el comportamiento del jugador en el contexto de su equipo.

Entregables:
- Detectar si las derrotas son correlacionadas con la composición del equipo.
- Detectar patrones en los roles de los compañeros en partidas perdidas.
- Requiere datos adicionales de la API (team compositions, ally stats).

### Sprint 9 — Champion Select y Meta
Objetivo: Recomendar picks basados en win rate personal y estado del meta.

Restricciones:
- Sin inventar datos de win rate globales.
- Solo usar historial personal del jugador.
- Meta: requiere datos de parche (Riot Data Dragon API).

---

## Deuda técnica pendiente

| Ítem | Prioridad | Descripción |
|------|-----------|-------------|
| Actualizar UI para usar scorer_v2 | Alta | La UI actual usa scorer.py V1 |
| Guardar CoachingResult en DB | Media | Ahora se calcula cada vez, no se persiste |
| Añadir pesos estadísticos a dimensiones | Baja | Requiere N≥50 por rol |
| Revisar cs_at_10 como señal (invertida) | Media | Con más datos puede resolverse |
| Test de regresión automático | Baja | Verificar que Sprint 1-3 no se rompen |

---

## Umbrales de datos necesarios para cada sprint

| Sprint | N ADC | N TOP | N MID | N JGL | N SUP |
|--------|-------|-------|-------|-------|-------|
| 4 (UI) | ≥20 ✓ | ≥1 ✓ | - | - | - |
| 5 (MID/JGL/SUP) | - | - | ≥10 | ≥10 | ≥10 |
| 6 (Progress) | ≥30 | ≥5 | - | - | - |
| 7 (Benchmarks) | - | - | - | - | - (dataset externo) |
