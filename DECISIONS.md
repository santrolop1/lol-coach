# DECISIONS.md — Decisiones técnicas y de diseño

Cada decisión incluye: qué se decidió, por qué, y qué alternativas se descartaron.

---

## D-01: Benchmarks auto-relativos (jugador vs sí mismo)

**Decisión:** Los scores se calculan como percentil del jugador dentro de su propio historial. Score 50 = rendimiento mediano propio.

**Por qué:** La API pública de Riot no provee distribuciones de métricas por elo para la mayoría de campos. Inventar valores (ej: "un ADC Gold debe tener 7.2 cs/min") sería una fabricación sin evidencia.

**Alternativa descartada:** Usar valores fijos de CS, KDA, etc. basados en guías online. Descartado por no ser verificables y por variar con cada patch.

**Implicación:** Un jugador que siempre juega mal tendrá scores de ~50 en todo. Es correcto en términos relativos pero no diagnóstico en absoluto. Se mitiga con los umbrales de coaching (D-07).

---

## D-02: Pesos iguales entre métricas de cada dimensión

**Decisión:** Dentro de cada dimensión (ej: Economy = cs_per_min + cs_at_10 + gold_per_min), cada métrica tiene peso 1/N.

**Por qué:** Con N=28 ADC partidas (WIN=11, LOSS=17), el error estándar de pesos derivados de regresión logística supera el 30%. No hay base estadística para pesos asimétricos.

**Cuándo revisar:** Cuando N≥50 partidas por rol. Se podrá calcular la correlación de cada métrica con win/loss y asignar pesos proporcionales.

**Excepción documentada:** `kill_participation` es el mayor discriminador en el dataset actual (delta WIN-LOSS = +0.106) pero no se le da más peso para mantener coherencia con el principio.

---

## D-03: Scoring no-paramétrico (percentile rank)

**Decisión:** score = fracción de partidas propias donde la métrica es ≤ valor actual × 100.

**Por qué:** No asume distribución normal. Robusto ante outliers (ej: una partida con 20 muertes no distorsiona todo el sistema). Simple de implementar y explicar.

**Alternativa descartada:** Z-score normalización. Requiere asumir distribución normal, sensible a outliers, produce valores negativos difíciles de comunicar al usuario.

---

## D-04: Sin IA, sin LLM, sin ML en el coaching engine

**Decisión:** El coaching usa exclusivamente reglas deterministas y datos calculados. Cero dependencia de modelos externos.

**Por qué:** Los LLMs inventan métricas. Las reglas son auditables, reproducibles y no tienen costos de inferencia por partida. El usuario puede entender exactamente por qué recibe cada recomendación.

**Alternativa descartada:** Llamar a un LLM para generar el texto de coaching. Descartado porque la evidencia cuantitativa (números reales) es más valiosa que texto generado, y porque introduce dependencia externa costosa.

---

## D-05: SQLite en lugar de PostgreSQL

**Decisión:** Base de datos local SQLite en `data/lol_coach.db`.

**Por qué:** Aplicación de un solo usuario, uso local. SQLite elimina la necesidad de servidor, instalación y configuración. El dataset máximo esperado es ~1000 partidas, dentro de los límites de SQLite.

**Cuándo reconsiderar:** Si se añade multi-usuario o acceso web concurrente.

---

## D-06: Normalización por duración para surrenders

**Decisión:** Métricas de volumen (gold, daño, objetivos) se expresan por minuto. Las partidas rendidas (game_ended_surrender=1) se incluyen en el análisis con esta normalización.

**Por qué:** Una partida de 15 minutos rendida tiene menos gold total que una de 35 minutos. Sin normalización, las partidas rendidas siempre parecerían economías malas. Con gold/min, son comparables.

**Impacto documentado:** cs_at_10 en surrenders puede ser 3 (Draven surrender en datos reales, partida ~8 minutos). Se marca la partida como rendida pero se incluye.

---

## D-07: Umbrales de coaching con dos fuentes

**Decisión:** Los umbrales de las reglas de coaching tienen fuente documentada: "research" (arquitectura V2, evidencia de coaching profesional) o "data" (percentiles del jugador).

**Por qué:** Transparencia. Si el umbral viene de investigación externa, el usuario debe saber que no es del dataset local. Si viene de sus propios datos, puede verificarlo.

**Ejemplo:** Deaths>6 para ADC es "research" (validado en dataset local: WIN=5.75, LOSS=7.82). KP<50% es "research". Economy score<40 es "data" (P40 de distribución propia).

---

## D-08: Regresión OLS para tendencia, no rolling average

**Decisión:** La tendencia usa regresión lineal OLS sobre todos los overall_scores ordenados por fecha.

**Por qué:** Rolling average (promedio móvil) depende del tamaño de la ventana, que con N=28 es arbitrario. OLS usa todos los datos y da una pendiente única y estable.

**Umbral:** ±1.5 pts/partida. En 10 partidas = ±15 puntos. Justificación: menos de 15 puntos de cambio en 10 partidas es ruido estadístico con la desviación típica observada (~15-25 puntos).

---

## D-09: Separación coaching_rules.py / coaching_engine.py

**Decisión:** Los textos, umbrales y planes de acción están en `coaching_rules.py` (datos puro). La lógica de evaluación está en `coaching_engine.py`.

**Por qué:** Permite actualizar textos de coaching sin tocar la lógica. Permite añadir nuevos roles (MID/JGL/SUP) añadiendo entradas en coaching_rules.py antes de implementar la evaluación.

**Alternativa descartada:** Tener todo en coaching_engine.py. Descartado por mezclar datos y lógica, dificultando el mantenimiento.

---

## D-10: Coexistencia scorer.py V1 y scorer_v2.py

**Decisión:** Se mantiene el scorer V1 original intacto. El V2 es un archivo nuevo paralelo.

**Por qué:** La UI actual depende de scorer.py V1. Reemplazarlo rompería la UI hasta que se actualice. La coexistencia permite desarrollar V2 sin romper el flujo existente.

**Restricción establecida:** `scorer.py` y `recommendations.py` NO se modifican hasta que la UI esté preparada para V2. Esta restricción fue establecida explícitamente al inicio del proyecto.

---

## D-11: CV para consistencia (no desviación estándar simple)

**Decisión:** Consistency score = max(0, 100 − CV), donde CV = (std / |mean|) × 100.

**Por qué:** La desviación estándar absoluta no es comparable entre jugadores con niveles diferentes. Un std de 20 es mucho más variable para alguien con media 30 que para alguien con media 80. CV es el coeficiente relativo.

**Ejemplo verificado:** [90,90,90,10,10] → consistency=24.5. [58,58,58,58,58] → consistency=100.0.

---

## D-12: primary_problem = máxima severidad, no mínimo score de dimensión

**Decisión:** El problema principal del coaching se selecciona por severidad (distancia del umbral × peso relativo), no por la dimensión con peor score de scorer_v2.

**Por qué:** TILT_SESSION siempre tiene severity=90 (urgencia de sesión supera análisis de habilidades). Una racha de 7 derrotas es más urgente que tener economy_score=45. La severidad captura urgencia; el score de dimensión no.

**Nota:** La dimensión con peor score del scorer_v2 se sigue mostrando en improvements (problemas secundarios).
