"""
Tryndamere — Champion Gold Standard.

Este es el primer perfil completo de la Game Intelligence Platform.
Sirve como referencia oficial para todos los campeones futuros.

Convención:
  PROFILE: ChampionProfile  ← exportado, cargado por ChampionRegistry
"""

from backend.game_intelligence.models.champion import (
    ChampionProfile, AbilityInfo,
    Combo, AnimationCancel, PowerSpike,
    ChampionMacroConfig, ChampionWaveConfig,
    ChampionBuildConfig, ChampionRuneConfig,
)
from backend.game_intelligence.models.common import KnowledgeSource, Confidence, SourceType

_SOURCE = KnowledgeSource(
    type=SourceType.COMMUNITY,
    author="GI Platform",
    confidence=Confidence.HIGH,
    date="2024-12",
    url=None,
    notes="Perfil creado como Gold Standard para la plataforma.",
)

PROFILE = ChampionProfile(
    # ── Identidad ─────────────────────────────────────────────────────────────
    champion="tryndamere",
    display_name="Tryndamere",
    roles=["TOP"],
    difficulty="medium",
    patch_version="14.12",
    identity=(
        "Guerrero de básicos con daño crítico que se vuelve imparable al escalar. "
        "Domina el split push tardío y puede sobrevivir cualquier situación con su R."
    ),
    playstyle="scaling",
    scaling="late",

    # ── Fortalezas ────────────────────────────────────────────────────────────
    strengths=[
        "1v1 tardío extremadamente poderoso con 2+ ítems de crit.",
        "Invulnerabilidad de 5 segundos (R) — permite recuperar vida con Q.",
        "Alto DPS sostenido gracias a crit + velocidad de ataque.",
        "Fuerte split pusher — E para escapar de cualquier rotación.",
        "La Q con alta furia cura masivamente — sustain sin items de vida.",
        "Escalado potente hacia late game — domina cuando hay recursos.",
    ],
    weaknesses=[
        "Extremadamente débil en early game (niveles 1-5) sin furia.",
        "Dependiente de la oleada de básicos — campeones con Blind (Teemo) lo anulan.",
        "Sin dash horizontal genuino — E va en línea recta predecible.",
        "Mala rotación al mid game — no tiene movilidad global.",
        "Muy dependiente de los ítems — necesita farm y oro para ser efectivo.",
        "La R tiene un cooldown muy largo (110s) — no puede usarla en cada pelea.",
    ],

    # ── Habilidades ───────────────────────────────────────────────────────────
    abilities={
        "P": AbilityInfo(
            key="P",
            name="Bloodlust (Pasiva)",
            description=(
                "Tryndamere gana Furia con cada básico y cuando mata enemigos. "
                "La Furia decae tras 8 segundos fuera de combate. "
                "Al activar Q (Battle Fury), consume toda la Furia para curar. "
                "A 100 de Furia: máxima curación y máximo crit chance."
            ),
            tips=[
                "Mantener alta la Furia antes de entrar en un intercambio.",
                "No usar Q cuando tienes poca Furia — la curación es mínima.",
                "Entrar en bush para farmear tropas acumula Furia sin ser atacado.",
            ],
            common_mistakes=[
                "Usar Q con poca Furia (bajo 50%) — cura mucho menos.",
                "Perder la Furia por estar fuera de combate demasiado tiempo antes de pelear.",
            ],
            cooldowns=[],
            max_rank_priority=3,
        ),
        "Q": AbilityInfo(
            key="Q",
            name="Battle Fury (Q)",
            description=(
                "Activo: consume toda la Furia actual para curar. "
                "La curación escala con la Furia consumida y con el HP máximo. "
                "A 100 Furia: curación masiva (puede curar hasta 400+ HP). "
                "Pasivo: aumenta el chance de crítico según la Furia actual "
                "(0 Furia = 0% crit extra, 100 Furia = 35% crit extra)."
            ),
            tips=[
                "Usar siempre a máxima Furia (100) para maximizar la curación.",
                "Si estás en peligro, entrar en combat para generar Furia rápido antes de Q.",
                "Con Spirit Visage: la curación de Q se amplifica un 25%.",
            ],
            common_mistakes=[
                "Usar Q inmediatamente al entrar en combate — no has generado suficiente Furia.",
                "Olvidar que Q también potencia el crit pasivamente — farmear con alta Furia.",
                "Usar Q antes de entrar en pelea en lugar de dentro de la pelea.",
            ],
            cooldowns=[12.0, 10.5, 9.0, 7.5, 6.0],
            cost="Consume toda la Furia",
            max_rank_priority=3,
            source=_SOURCE,
        ),
        "W": AbilityInfo(
            key="W",
            name="Mocking Shout (W)",
            description=(
                "Grito que desacelera a todos los enemigos a los que Tryndamere NO está mirando "
                "y reduce el AD de todos los enemigos en el rango. "
                "Los enemigos de espaldas reciben lentitud masiva."
            ),
            tips=[
                "Usar W cuando el enemigo está huyendo de espaldas — máxima lentitud.",
                "Útil en teamfights para reducir el AD de los carries enemigos.",
                "Combinar con E: E para alcanzar al enemigo que huye con W activo.",
            ],
            common_mistakes=[
                "Usar W cuando el enemigo te está mirando — no recibe el slow.",
                "No usar W en peleas — la reducción de AD es significativa.",
            ],
            cooldowns=[14.0, 14.0, 14.0, 14.0, 14.0],
            cost="Sin coste",
            max_rank_priority=2,
            source=_SOURCE,
        ),
        "E": AbilityInfo(
            key="E",
            name="Spinning Slash (E)",
            description=(
                "Dash en línea recta. Hace daño físico a todos los enemigos en el camino. "
                "El cooldown se reduce significativamente con cada básico crítico (1.5s por crítico). "
                "A full crit: el cooldown puede ser casi inexistente."
            ),
            tips=[
                "El E no interrumpe básicos — puede usarse dentro del combo de ataque.",
                "Con alta probabilidad de crítico: el E está disponible casi constantemente.",
                "Guardar E para escapar — nunca desperdiciar en iniciar sin poder salir.",
                "E a través de paredes en puntos específicos del mapa.",
            ],
            common_mistakes=[
                "Usar E para iniciar y quedarse sin escape — morir innecesariamente.",
                "No usar E para escapar de una rotación 2v1 en el split.",
                "Usar E perpendicular al objetivo — solo va en línea recta.",
            ],
            cancel_windows=[
                "El dash de E puede cancelarse con un básico anterior (técnica avanzada).",
            ],
            cooldowns=[13.0, 12.0, 11.0, 10.0, 9.0],
            cost="Sin coste",
            max_rank_priority=1,
            source=_SOURCE,
        ),
        "R": AbilityInfo(
            key="R",
            name="Undying Rage (R)",
            description=(
                "Tryndamere entra en rabia que lo hace invulnerable durante 5 segundos. "
                "Durante la R: no puede morir aunque llegue a 0 HP. "
                "Gana Furia masiva al activarse. "
                "Cooldown largo: 110/100/90 segundos."
            ),
            tips=[
                "Activar ANTES de llegar a 0 HP — si llegas a 0 sin R, mueres.",
                "El timing ideal es entre 15-25% de HP para maximizar la curación con Q dentro.",
                "Con alta Furia al activar: curar masivamente con Q durante los 5 segundos.",
                "La R + Q puede recuperar 600+ HP en 5 segundos con buena Furia.",
                "La R no puede activarse si ya estás a 0 HP — no esperar demasiado.",
            ],
            common_mistakes=[
                "Activar R demasiado tarde — llegar a 0 HP antes de activarla.",
                "Activar R innecesariamente — desperdiciar el cooldown de 110s.",
                "No curar con Q dentro de la R — perder la ventana de curación.",
                "Usar R cuando el enemigo tiene Ignite activo — reduce la curación de Q.",
            ],
            cooldowns=[110.0, 100.0, 90.0],
            cost="Sin coste",
            max_rank_priority=1,  # subir primero (solo 3 niveles)
            source=_SOURCE,
        ),
    },
    ability_order=["E", "Q", "W"],  # E primero, luego Q, W último

    # ── Combos ────────────────────────────────────────────────────────────────
    combos=[
        Combo(
            id="basic_trade",
            name="Intercambio básico",
            sequence=["AA", "Q (cuando hay Furia)", "AA", "AA"],
            description=(
                "El combo estándar de intercambio. "
                "Usar Q para regenerar entre básicos cuando la Furia está alta."
            ),
            when_to_use="Intercambios de low commitment en la fase de carriles.",
            difficulty="basic",
            timing_notes="Curar con Q cuando la Furia supera el 70%.",
        ),
        Combo(
            id="all_in_r",
            name="All-in con R",
            sequence=["AA", "AA", "AA", "R (al 20% HP)", "Q", "AA", "AA", "AA", "W+E si huye"],
            description=(
                "El combo completo de all-in. Atacar hasta bajar al 20% de HP, "
                "activar R, curar masivamente con Q dentro de la R, "
                "y seguir atacando durante los 5 segundos de invulnerabilidad."
            ),
            when_to_use="All-in decidido — cuando el enemigo está bajo de vida o comprometido.",
            difficulty="intermediate",
            timing_notes=(
                "La clave es la Furia al activar R — cuanta más Furia, más cura Q. "
                "Tener 80+ de Furia antes de comprometerse completamente."
            ),
        ),
        Combo(
            id="escape_sequence",
            name="Secuencia de escape",
            sequence=["W (hacia el enemigo)", "E (en dirección opuesta)", "AA (si puede)"],
            description=(
                "Usar W para slow al perseguidor (de espaldas) y E para escapar. "
                "El slow de W facilita salir del rango."
            ),
            when_to_use="Cuando el enemigo te está cazando con ventaja.",
            difficulty="basic",
            timing_notes="W primero para que el enemigo esté de espaldas al usar E.",
        ),
        Combo(
            id="tower_dive_r",
            name="Dive bajo torre con R",
            sequence=["E (iniciar)", "AA", "AA", "R (cuando la torre te ataca)", "Q", "Kill", "E (salir)"],
            description=(
                "Dive bajo torre usando la R para aguantar el daño. "
                "Activar R cuando la torre empieza a atacar. "
                "Curar con Q dentro de la R."
            ),
            when_to_use="Cuando el enemigo tiene muy poca vida bajo su propia torre.",
            difficulty="advanced",
            timing_notes=(
                "Calcular que tienes suficiente daño para matar antes de que expire la R. "
                "Necesitar E de vuelta para escapar."
            ),
        ),
    ],

    # ── Animation Cancels ────────────────────────────────────────────────────
    animation_cancels=[
        AnimationCancel(
            id="e_animation_cancel",
            name="E durante básico",
            sequence=["Inicio de AA", "E inmediato", "AA llega + dash activa"],
            description=(
                "Activar E justo después de iniciar un básico. "
                "El básico llega al objetivo mientras Tryndamere empieza el dash. "
                "Permite más mobilidad sin perder DPS."
            ),
            difficulty="intermediate",
            practice_drill_id="animation_cancel_fundamentals",
        ),
    ],

    # ── Power Spikes ─────────────────────────────────────────────────────────
    power_spikes=[
        PowerSpike(
            id="level_6",
            timing="Nivel 6",
            description="Desbloquear R — se vuelve extremadamente difícil de matar.",
            action=(
                "Con nivel 6: aceptar intercambios más agresivos sabiendo que R salva. "
                "Es el punto donde el matchup contra muchos enemigos se iguala."
            ),
            window_minutes=(8.0, 12.0),
            enemy_spike_context=(
                "También es cuando muchos enemigos (Darius, Garen) tienen su R. "
                "No activar R si el enemigo puede R-ejecutar inmediatamente."
            ),
        ),
        PowerSpike(
            id="first_item",
            timing="Primer ítem completado (Trinity Force / Kraken)",
            description=(
                "El daño aumenta masivamente. Los intercambios 1v1 se vuelven "
                "consistentemente favorables contra la mayoría de enemigos."
            ),
            action=(
                "Empezar a presionar más agresivamente el carril. "
                "Iniciar el split push hacia el primer objetivo estructural."
            ),
            window_minutes=(14.0, 20.0),
            enemy_spike_context=(
                "Los carries enemigos también tienen sus primeros ítems. "
                "No asumir dominancia automática — verificar el matchup específico."
            ),
        ),
        PowerSpike(
            id="two_items",
            timing="Dos ítems completados (Trinity + PD / Kraken + PD)",
            description=(
                "Tryndamere domina el 1v1 contra casi todos los top laners. "
                "La velocidad de ataque con Phantom Dancer y el crit hace daño masivo."
            ),
            action=(
                "Establecer split push permanente. "
                "Solo abandonar el split si el equipo necesita 5v4."
            ),
            window_minutes=(22.0, 30.0),
        ),
        PowerSpike(
            id="full_build",
            timing="Full build (4-5 ítems)",
            description=(
                "Tryndamere está en su punto máximo. "
                "Con la R puede aguantar el 1v3 en muchos casos. "
                "La ventana de invulnerabilidad + curación es casi irremontable."
            ),
            action=(
                "Jugar para el Nexus. "
                "El 1v5 con R activa puede ganar la partida desde atrás."
            ),
            window_minutes=(35.0, 99.0),
        ),
    ],

    # ── Configuraciones (solo IDs — nunca duplicar conocimiento) ─────────────
    macro_config=ChampionMacroConfig(
        primary_pattern_ids=["split_push", "recall_timing", "side_lane_pressure"],
        win_condition_ids=["split_and_win"],
        split_push_priority="always",
        teamfight_role="frontline",
    ),

    wave_config=ChampionWaveConfig(
        preferred_technique_ids=["crash", "freeze", "slow_push"],
        level_2_crash=False,  # Tryndamere no tiene ventaja de crash al nivel 2
        recall_setup_technique_id="crash",
    ),

    build_config=ChampionBuildConfig(
        standard_build_id="tryndamere_standard_crit",
        vs_tanks_build_id="tryndamere_vs_tanks",
        vs_poke_build_id="tryndamere_vs_poke",
        vs_burst_build_id=None,
        starter_id="long_sword",
        boots_options=["plated_steelcaps", "mercury_treads"],
    ),

    rune_config=ChampionRuneConfig(
        standard_page_id="lethal_tempo_crit",
        vs_poke_page_id="tryndamere_grasp",
        vs_all_in_page_id="tryndamere_grasp",
    ),

    # ── Conocimiento editorial ────────────────────────────────────────────────
    common_mistakes=[
        "Activar R demasiado tarde — esperar hasta 0 HP cuando ya es imposible activar.",
        "Usar Q con poca Furia (< 50) — curación mínima, desperdicio del CD.",
        "No guardar E para escapar — usar E para iniciar y morir sin escape.",
        "Intentar ganar el carril en early con campeones que dominan ese período.",
        "Hacer peleas sin R disponible cuando el CD es largo.",
        "No split pushear en late game — quedarse con el equipo en teamfights perdibles.",
        "Construir ítems de survivability antes de daño — Tryndamere necesita matar rápido.",
        "Olvidar generar Furia antes de un intercambio importante.",
    ],
    tips=[
        "La R es tu mayor recurso — úsala con cabeza. 110s de CD es mucho tiempo.",
        "Split push es la Win Condition. No teamfight si no es necesario.",
        "E es tu escape — nunca entres en una pelea sin poder salir.",
        "Alta Furia antes de pelear = más curación con Q = más tiempo de vida.",
        "Con 2+ ítems puedes pelear casi a cualquier top laner en el 1v1.",
        "Compra Control Wards cuando spliteas — la visión es tu protección.",
        "Aprende el timing de la R: activa entre 15-25% HP para maximizar Q.",
    ],

    # ── Learning ──────────────────────────────────────────────────────────────
    learning_roadmap_id="tryndamere_top_v1",

    # ── Metadatos ─────────────────────────────────────────────────────────────
    sources=[_SOURCE],
    last_updated="2024-12",
)
