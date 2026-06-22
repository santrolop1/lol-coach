"""
coaching_rules.py — Definiciones de reglas de coaching.

Este archivo contiene únicamente datos: textos, templates, umbrales y fuentes.
La lógica de evaluación está en coaching_engine.py.

Principio de diseño:
  Cada regla tiene su umbral documentado con su fuente.
  "research"  → evidencia de coaching profesional / Arquitectura V2
  "data"      → calculado desde distribución histórica del jugador
  "hybrid"    → combina umbral absoluto con percentil del jugador
"""


# ---------------------------------------------------------------------------
# Umbrales de detección
# ---------------------------------------------------------------------------
#
# Para cada métrica se define:
#   threshold: valor numérico de corte
#   source:    de dónde proviene el umbral
#   direction: 'above' = problema si el valor SUPERA el umbral
#               'below' = problema si el valor está POR DEBAJO del umbral
#
# Fuentes research (Arquitectura V2, coaching profesional):
#   ADC Gold/Plat: deaths >6, KP <50%, CS@10 <55, consistency <65
#   TOP Gold/Plat: deaths >5, CS@10 <60

THRESHOLDS = {
    "ADC": {
        "deaths_high": {
            "value": 6.0,
            "source": "research",
            "direction": "above",
            "note": "ADC en Gold/Plat no debería promediar >6 muertes. "
                    "Validado en este dataset: WIN avg=5.75, LOSS avg=7.82 (delta=2.07).",
        },
        "kill_participation_low": {
            "value": 0.50,
            "source": "research",
            "direction": "below",
            "note": "ADC en Gold debería participar en >50% de kills. "
                    "Validado en dataset: WIN avg=0.475 vs LOSS avg=0.407.",
        },
        "cs_at_10_low": {
            "value": 55,
            "source": "research",
            "direction": "below",
            "note": "ADC en Gold debería llegar a 55+ CS a los 10 min. "
                    "ADVERTENCIA: en este dataset CS@10 NO correlaciona con wins "
                    "(WIN=43.7 vs LOSS=47.5). Posible sesgo de muestra pequeña. "
                    "Se mantiene la regla por evidencia externa pero con baja confianza.",
        },
        "economy_score_low": {
            "value": 40.0,
            "source": "data",
            "direction": "below",
            "note": "Dimensión Economy en P40 de distribución propia.",
        },
        "positioning_score_low": {
            "value": 40.0,
            "source": "data",
            "direction": "below",
        },
        "combat_score_low": {
            "value": 40.0,
            "source": "data",
            "direction": "below",
        },
        "consistency_low": {
            "value": 65.0,
            "source": "hybrid",
            "direction": "below",
            "note": "CV > 35% (std/mean > 0.35) indica nivel inestable.",
        },
        "floor_ceiling_gap_high": {
            "value": 40.0,
            "source": "data",
            "direction": "above",
            "note": "Diferencia entre P75 y P25 del overall score.",
        },
        "tilt_consecutive_losses": {
            "value": 4,
            "source": "research",
            "direction": "above",
            "note": "4+ derrotas consecutivas en un mismo día indica tilt activo.",
        },
        "losing_streak": {
            "value": 3,
            "source": "research",
            "direction": "above",
            "note": "3+ derrotas seguidas (sin restricción de día).",
        },
    },
    "TOP": {
        "deaths_high": {
            "value": 5.0,
            "source": "research",
            "direction": "above",
            "note": "TOP en Gold/Plat no debería promediar >5 muertes.",
        },
        "cs_at_10_low": {
            "value": 60,
            "source": "research",
            "direction": "below",
            "note": "TOP en Gold debería llegar a 60+ CS a los 10 min.",
        },
        "pressure_score_low": {
            "value": 40.0,
            "source": "data",
            "direction": "below",
        },
        "lane_score_low": {
            "value": 40.0,
            "source": "data",
            "direction": "below",
        },
        "consistency_low": {
            "value": 65.0,
            "source": "hybrid",
            "direction": "below",
        },
        "tilt_consecutive_losses": {
            "value": 4,
            "source": "research",
            "direction": "above",
        },
    },
}


# ---------------------------------------------------------------------------
# Definiciones de problemas — ADC
# ---------------------------------------------------------------------------

ADC_PROBLEMS = {

    "TILT_SESSION": {
        "name":           "Sesión de tilt activa",
        "display_name":   "Sesión de tilt activa",
        "probable_cause": (
            "Jugar 4+ partidas perdidas consecutivas en el mismo día crea un "
            "ciclo de malas decisiones. Cada derrota aumenta la frustración, "
            "reduce la concentración y deteriora la toma de decisiones."
        ),
        "impact": (
            "Las partidas jugadas en tilt tienen peor KDA y kill participation "
            "que el promedio personal. El jugador tiende a forzar peleas "
            "y tomar riesgos innecesarios para 'recuperar' las partidas."
        ),
        "primary_action": (
            "Detén la sesión ranked ahora. "
            "Juega 1 partida normal o descansa mínimo 30 minutos "
            "antes de volver a ranked."
        ),
        "secondary_actions": [
            "Revisa qué fue diferente en tu última victoria antes de la racha. "
            "No busques errores en las derrotas — busca lo que hacías bien antes.",
            "El objetivo para hoy no es subir de elo. "
            "El objetivo es cortar la racha con calidad, no con cantidad.",
        ],
        "goal_template":     "Ganar 1 partida ranked con <{target_deaths:.0f} muertes antes de terminar la sesión.",
        "strength_not_applicable": True,
    },

    "HIGH_DEATHS": {
        "name":           "Exceso de muertes",
        "display_name":   "Exceso de muertes",
        "probable_cause": (
            "El ADC muere más en partidas perdidas que en victorias. "
            "Las causas más comunes son: posicionarse demasiado adelante en teamfights, "
            "entrar a peleas sin información de visión, o intentar duelos "
            "que el champion no puede ganar."
        ),
        "impact": (
            "Cada muerte genera tiempo muerto, bounties para el rival y cede "
            "presión de mapa. Un ADC muerto no hace daño, no contesta objetivos "
            "y no presiona torres."
        ),
        "primary_action": (
            "Antes de cada teamfight identifica al campeón de engage rival. "
            "No avances más que el aliado melee más cercano. "
            "Si el engage enemigo no ha usado su CC, no entres."
        ),
        "secondary_actions": [
            "Si tienes 3+ muertes en los primeros 15 minutos, cambia el objetivo: "
            "solo CS seguro. No pelees más en lane hasta recomponer.",
            "Después de cada muerte, pregunta: '¿Tenía visión del punto de entrada?' "
            "Si la respuesta es no, el problema es visión, no mecánicas.",
        ],
        "goal_template":    "Reducir muertes de {current:.1f} a {target:.1f} en las próximas 10 partidas.",
    },

    "LOW_KILL_PARTICIPATION": {
        "name":           "Baja participación en peleas",
        "display_name":   "Baja participación en peleas de equipo",
        "probable_cause": (
            "El ADC está farmeando cuando el equipo está peleando. "
            "O llega tarde a las peleas de Dragon y Baron. "
            "Kill participation es un indicador de presencia en momentos clave."
        ),
        "impact": (
            "Un ADC ausente en teamfights cede el daño de carry al equipo. "
            "El equipo pelea en desventaja de daño y pierde peleas que debería ganar."
        ),
        "primary_action": (
            "Cuando Dragon o Baron aparecen en el mapa, ve a la zona 1 minuto antes. "
            "El farmeo durante un Dragon fight raramente compensa lo que se pierde."
        ),
        "secondary_actions": [
            "Si hay una pelea activa y tu posición en el mapa no te permite llegar en 10 "
            "segundos, es una señal de que estabas mal posicionado antes de la pelea.",
            "En mid/late game, muévete con tu equipo cuando pase el minuto 20. "
            "El farmeo en solitario tiene rendimientos decrecientes.",
        ],
        "goal_template":    "Subir kill participation de {current:.0%} a {target:.0%} en las próximas 10 partidas.",
    },

    "LOW_CS_AT_10": {
        "name":           "CS deficiente en early game",
        "display_name":   "Farm deficiente en fase de líneas",
        "probable_cause": (
            "Muertes tempranas que interrumpen el patrón de farm, "
            "mala gestión de la ola (pushing cuando deberías freeze), "
            "o perder CS por pelear en lugar de farmear."
        ),
        "impact": (
            "Cada 10 CS = ~300 gold. Llegar a la primera base con 30 CS "
            "menos que el rival es un componente de item de desventaja."
        ),
        "primary_action": (
            "En los primeros 10 minutos, el objetivo primario es CS. "
            "No pelees a menos que el kill sea 100% seguro o que el rival "
            "te ataque primero. Cada pelea arriesgada que no resulta en kill "
            "interrumpe tu patrón de farm."
        ),
        "secondary_actions": [
            "Practica CS en modo entrenamiento (5 min sin items): "
            "el objetivo es llegar a 60 CS en 10 minutos. "
            "Cuando lo logres en práctica, lo lograrás en ranked.",
            "Si el jungler rival aparece en tu lane antes del minuto 8, "
            "haz recall y resetea. No intentes recuperar CS muriéndote.",
        ],
        "goal_template":    "Llegar a {target:.0f} CS al minuto 10 de forma consistente.",
        "data_note":        (
            "NOTA: En este dataset, CS@10 NO correlaciona con victorias "
            "(WIN avg={win_cs10:.1f} vs LOSS avg={loss_cs10:.1f}). "
            "Este objetivo se basa en evidencia externa, no en los datos locales."
        ),
    },

    "LOW_OBJECTIVE_CONTRIBUTION": {
        "name":           "Baja contribución a objetivos",
        "display_name":   "Baja contribución a objetivos del mapa",
        "probable_cause": (
            "El ADC no está presente en las peleas de Dragon y Baron. "
            "O llega muerto cuando el equipo va a tomar objetivos."
        ),
        "impact": (
            "Dragon soul y Baron buff son los multiplicadores de cierre de partida "
            "más importantes. Cada Dragon perdido = el rival acumula stacks."
        ),
        "primary_action": (
            "Sigue el ciclo Dragon: cada vez que Dragon aparezca en el minimapa, "
            "muévete hacia bot side si estás libre. "
            "El DPS del ADC es crucial en los Smite races."
        ),
        "secondary_actions": [
            "Activa el timer de Dragon. Si juegas sin timers de objetivos, "
            "estás dependiendo de que el equipo te avise.",
            "Si estás splitpusheando cuando Dragon aparece, evalúa: "
            "¿vale más la torre que el Dragon? En la mayoría de elos, no.",
        ],
        "goal_template":    "Aumentar damage_to_objectives de {current:.0f} a {target:.0f} por partida.",
    },

    "HIGH_INCONSISTENCY": {
        "name":           "Nivel inconsistente",
        "display_name":   "Alto rango de variación entre partidas",
        "probable_cause": (
            "Pool de campeones demasiado amplio. "
            "El nivel cambia drásticamente dependiendo del champion pick, "
            "del match-up, o del estado mental al empezar la partida."
        ),
        "impact": (
            "La inconsistencia hace el elo difícil de subir: "
            "se ganan partidas brillantes pero se pierden partidas evitables. "
            "El suelo del jugador, no el techo, determina el elo real."
        ),
        "primary_action": (
            "Reduce tu pool a 2 champions para ranked esta semana. "
            "La maestría en 2 campeones consistentes genera más LP que "
            "el potencial de 5 campeones dominados a medias."
        ),
        "secondary_actions": [
            "Identifica en qué champions tienes los peores scores (los 10, 20 de overall). "
            "Esos son los candidates a sacar del pool ranked.",
            "La partida que menos control tienes es la que más daño hace a tu elo. "
            "Sube tu suelo antes de intentar subir tu techo.",
        ],
        "goal_template":    "Mantener overall score entre {floor:.0f} y {ceiling:.0f} en las próximas 10 partidas.",
    },
}


# ---------------------------------------------------------------------------
# Definiciones de problemas — TOP
# ---------------------------------------------------------------------------

TOP_PROBLEMS = {

    "TILT_SESSION": {
        "name":           "Sesión de tilt activa",
        "display_name":   "Sesión de tilt activa",
        "probable_cause": (
            "4+ derrotas consecutivas en el mismo día generan toma de decisiones "
            "reactiva. TOP es especialmente sensible porque las malas decisiones "
            "de split push y TP resultan en derrotas irreversibles."
        ),
        "impact": (
            "Los TPs del TOP bajo tilt tienden a ser reactivos (defensivos) "
            "en lugar de proactivos (ofensivos). Se pierde el mayor valor "
            "diferenciador del rol."
        ),
        "primary_action": (
            "Detén la sesión ranked. "
            "Si no puedes dejar de jugar, al menos juega en normal para "
            "resetear el estado mental sin arriesgar LP."
        ),
        "secondary_actions": [
            "Revisa la última partida ganada antes de la racha. "
            "¿Qué TP tomaste? ¿Cuándo vas a splitpush vs cuando unirte al equipo?",
            "El tilt en TOP manifesta como: mucho splitpush sin presión real, "
            "TP tardíos, y pelear cuando deberías estar tanqueando.",
        ],
        "goal_template":     "Ganar 1 partida con <{target_deaths:.0f} muertes y {target_tt:.0f}+ torres.",
        "strength_not_applicable": True,
    },

    "HIGH_DEATHS_TOP": {
        "name":           "Exceso de muertes TOP",
        "display_name":   "Exceso de muertes en top lane",
        "probable_cause": (
            "Morir en top lane antes de que el jungler pueda responder, "
            "sobreextenderse sin visión de river, "
            "o intentar peleas que el champion no puede ganar en ese estado de items."
        ),
        "impact": (
            "Cada muerte en top cede bounty y presencia de mapa en el side más lejano. "
            "Un top muerto no puede presionar para el primer Dragon "
            "ni responder al Herald."
        ),
        "primary_action": (
            "Coloca una Control Ward en el arbusto de river de top antes del minuto 5. "
            "La mayoría de muertes tempranas en top son ganks sin visión previa. "
            "Si ves el arbusto, ves el gank antes de que sea fatal."
        ),
        "secondary_actions": [
            "Si el rival tienes más de 30 CS que tú y sus jungler está missing, "
            "retrocede a tu turret. La turret evita 2 de cada 3 ganks.",
            "Recuerda el principio de 'farm safe after death': "
            "si mueres una vez, la siguiente vez solo farmeas bajo turret.",
        ],
        "goal_template":    "Reducir muertes de {current:.1f} a {target:.1f} en las próximas 10 partidas.",
    },

    "BAD_LANE_PHASE": {
        "name":           "Mala fase de líneas",
        "display_name":   "Deficiencia en farm y control de lane",
        "probable_cause": (
            "Perder CS por miedo a intercambios de daño, "
            "no aprovechar ventanas de push cuando el rival tiene habilidades en cooldown, "
            "o no ajustar el estilo de farm al match-up específico."
        ),
        "impact": (
            "Una fase de líneas perdida en top significa llegar al mid game "
            "sin items completos, lo que reduce el impacto en teamfights "
            "y la capacidad de splitpush efectivo."
        ),
        "primary_action": (
            "Estudia el wave management básico de tu champion principal: "
            "cuándo hacer slow push, cuándo fast push y cuándo freeze. "
            "El CS no es solo mecánico — es saber qué hacer con la ola en cada situación."
        ),
        "secondary_actions": [
            "Practica el match-up específico donde más CS pierdes en modo personalizado. "
            "10 minutos de práctica del match-up específico vale más que 10 partidas.",
            "Antes del minuto 10, la prioridad es CS. "
            "Un kill que interrumpe 20 CS de farm raramente vale la pena.",
        ],
        "goal_template":    "Alcanzar {target:.0f} CS al minuto 10 de forma consistente.",
    },

    "LOW_PRESSURE": {
        "name":           "Baja presión lateral",
        "display_name":   "Baja conversión de ventaja en presión estructural",
        "probable_cause": (
            "El TOP gana su lane pero no convierte esa ventaja en torretas. "
            "Puede deberse a joining teamfights innecesarias cuando el split "
            "sería más valioso, o a no aprovechar las ventanas de push."
        ),
        "impact": (
            "Sin presión lateral, el equipo rival puede ejecutar su juego libremente. "
            "Una torreta vale más que un kill en términos de conversión a victoria."
        ),
        "primary_action": (
            "Cuando el equipo está en ventaja de items y tiene visión, "
            "el TOP debe splitpushear la side lane en lugar de agruparse. "
            "Fuerza al rival a responder con un jugador, dándole ventaja numérica a tu equipo."
        ),
        "secondary_actions": [
            "Aprende el TP math: ¿cuánto tiempo tarda en llegar al equipo? "
            "Si tienes Flash + TP disponibles, puedes splitpushear hasta 45 segundos antes del Dragon.",
            "Objetivo mínimo: en cada partida mayor de 25 minutos, "
            "deberías tener al menos 1 torre derribada.",
        ],
        "goal_template":    "Derribar {target:.0f}+ torres por partida en partidas >25 minutos.",
    },

    "HIGH_INCONSISTENCY_TOP": {
        "name":           "Nivel inconsistente TOP",
        "display_name":   "Alto rango de variación entre partidas",
        "probable_cause": (
            "Pool de campeones de TOP demasiado amplio para el elo actual, "
            "o los match-ups de TOP son tan variables que el resultado depende "
            "mucho del match-up específico."
        ),
        "impact": (
            "TOP tiene el match-up más especializado del juego. "
            "Un campeón mal conocido en un match-up difícil puede perder 30 CS "
            "por ser la primera vez que lo juega en ese match-up."
        ),
        "primary_action": (
            "Elige 1 campeón de TOP que conozcas profundamente y solo juega ese. "
            "El conocimiento de los timings de power spikes y los match-ups "
            "específicos vale más que 5 campeones a medias."
        ),
        "secondary_actions": [
            "Identifica los 3 match-ups más difíciles de tu campeón principal "
            "y estudia cómo los manejan los mejores jugadores de ese champion.",
            "Si el meta cambió y tu campeón fue nerfado, no es el momento de aprender "
            "un campeón nuevo en ranked. Usa normales para el nuevo pick.",
        ],
        "goal_template":    "Mantener overall score entre {floor:.0f} y {ceiling:.0f} en las próximas 10 partidas.",
    },

    "LOW_ADVANTAGE_CONVERSION": {
        "name":           "Baja conversión de ventaja de línea",
        "display_name":   "Ventaja de línea no convertida en presión estructural",
        "probable_cause": (
            "El TOP tiene control de su lane (CS razonable, ventaja en gold) "
            "pero no convierte esa ventaja en torres ni en presión estructural. "
            "Puede deberse a unirse a teamfights innecesarias cuando el split "
            "sería más valioso, o a no reconocer las ventanas de push."
        ),
        "impact": (
            "Ganar la lane y no convertirlo en torretas devuelve la ventaja al rival. "
            "Las torretas generan oro global para el equipo, despejan visión "
            "y crean presión de mapa que el rival está obligado a responder."
        ),
        "primary_action": (
            "Después de ganar un intercambio o forzar el recall del rival, "
            "pushea la ola y ve a la torre. "
            "La ventana de 15-20 segundos después de un recall es el momento clave. "
            "No esperes en lane sin convertir la presión en estructura."
        ),
        "secondary_actions": [
            "Practica el ciclo: freeze la ola, fuerza al rival a acercarse, "
            "consigue el intercambio favorable, luego fast push y ataca la torre.",
            "Si tienes 30+ CS de ventaja y tu equipo va por Dragon, "
            "considera TP-flank en lugar de seguir en lane — "
            "la ventaja ya existe, ahora convierte eso en el mapa.",
        ],
        "goal_template":    "Derribar {target:.0f}+ torre(s) en las próximas 10 partidas cuando tengas ventaja de línea.",
    },
}


# ---------------------------------------------------------------------------
# Definiciones de fortalezas — ADC
# ---------------------------------------------------------------------------

ADC_STRENGTHS = {
    "STRONG_ECONOMY": {
        "name":     "Eficiencia económica",
        "template": "CS/min promedio de {value:.2f} ({percentile:.0f}° percentil de tus partidas).",
    },
    "GOOD_POSITIONING": {
        "name":     "Buena supervivencia",
        "template": "Promedio de {value:.1f} muertes por partida, mejor que tu mediana histórica.",
    },
    "HIGH_KILL_PARTICIPATION": {
        "name":     "Buena presencia en peleas",
        "template": "Kill participation de {value:.0%} en promedio — participas en la mayoría de kills del equipo.",
    },
    "STRONG_COMBAT": {
        "name":     "Alto impacto en combate",
        "template": "{value:.0%} del daño total del equipo — estás cumpliendo el rol de carry de daño.",
    },
    "VISION_COMPLIANCE": {
        "name":     "Cumplimiento de visión",
        "template": "{value:.1f} Control Wards por partida — por encima del mínimo para tu rol.",
    },
    "CONSISTENCY": {
        "name":     "Nivel consistente",
        "template": "Consistency score de {value:.0f}/100 — tu rendimiento es predecible.",
    },
}


# ---------------------------------------------------------------------------
# Definiciones de fortalezas — TOP
# ---------------------------------------------------------------------------

TOP_STRENGTHS = {
    "STRONG_LANE": {
        "name":     "Dominio de fase de líneas",
        "template": "CS@10 promedio de {value:.0f} — bien por encima del benchmark.",
    },
    "GOOD_SURVIVAL_TOP": {
        "name":     "Buena supervivencia",
        "template": "Promedio de {value:.1f} muertes por partida para el rol TOP.",
    },
    "STRONG_PRESSURE": {
        "name":     "Buena presión lateral",
        "template": "{value:.0f} torres destruidas de media — presencia estructural consistente.",
    },
}


# ---------------------------------------------------------------------------
# Resúmenes de tendencia
# ---------------------------------------------------------------------------

TREND_SUMMARIES = {
    "improving": {
        "title":       "Mejorando",
        "description": (
            "Tu rendimiento ha mejorado en las últimas partidas. "
            "La pendiente de regresión es positiva: estás en la dirección correcta. "
            "Mantén lo que estás haciendo bien."
        ),
    },
    "stable": {
        "title":       "Estable",
        "description": (
            "Tu rendimiento es consistente pero no está mejorando activamente. "
            "Estás en un plateau. Identifica la dimensión con mayor brecha "
            "respecto a tu mejor nivel y trabájala deliberadamente."
        ),
    },
    "declining": {
        "title":       "Empeorando",
        "description": (
            "Tu rendimiento ha declinado en las últimas partidas. "
            "Evalúa si hay un factor externo (nuevo champion, cansancio, racha de malos match-ups) "
            "o si es un hábito que se está deteriorando."
        ),
    },
}


# ---------------------------------------------------------------------------
# Niveles de confianza
# ---------------------------------------------------------------------------

CONFIDENCE_DESCRIPTIONS = {
    "insufficient": (
        "Muestra insuficiente (N<5). "
        "El coaching es orientativo, no diagnóstico."
    ),
    "preliminary": (
        "Muestra preliminar (N=5-9). "
        "Las tendencias son visibles pero los benchmarks tienen alta varianza."
    ),
    "reliable": (
        "Muestra fiable (N=10-19). "
        "Los patrones son detectables y el coaching tiene base estadística."
    ),
    "robust": (
        "Muestra robusta (N≥20). "
        "Los diagnósticos son estadísticamente sólidos."
    ),
}
