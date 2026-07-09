"""
Biblioteca universal de Macro Patterns.

Patrones de macro reutilizables para cualquier campeón.
Los campeones referencian estos patrones por ID.
"""

from backend.game_intelligence.models.macro import MacroPattern

PATTERNS: list[MacroPattern] = [
    MacroPattern(
        id="split_push",
        name="Split Push",
        phase="mid_late",
        description=(
            "Presionar un carril lateral mientras el equipo amenaza al otro lado del mapa. "
            "El objetivo es crear un dilema 1v1 o 2v2 que el enemigo no puede resolver "
            "sin ceder objetivos o estructuras."
        ),
        when_to_apply=(
            "Cuando tu campeón domina el 1v1 o 2v2 en el carril lateral. "
            "Cuando tu equipo no puede ganar una pelea grupal directa. "
            "Cuando tienes ventaja en CS/oro sobre tu oponente de carril. "
            "Post-inhibidor para forzar defensas divididas."
        ),
        steps=[
            "Establece presencia en el carril lateral (top o bot) con visión.",
            "Empuja continuamente para forzar respuesta del equipo enemigo.",
            "Cuando 2+ enemigos rotan, tu equipo tiene ventaja 4v3 en el otro lado.",
            "Si nadie rota: sigue empujando y toma estructuras.",
            "Coordina con tu equipo para no hacer peleas cuando el split está activo.",
        ],
        anti_pattern=(
            "Unirse a peleas grupales en el mapa cuando el split push está generando presión. "
            "Esto cancela el dilema y da al enemigo exactamente lo que quiere."
        ),
        common_mistakes=[
            "Ir al split sin visión — morir hace que la presión se reverse.",
            "No comunicar al equipo que está en modo split.",
            "Hacer split cuando el enemigo tiene campeones con mucho TP y puede rotar.",
            "Luchar 1v2 cuando la rotación del equipo les da oportunidad de matar.",
        ],
        applies_to_roles=["TOP", "MID", "ADC"],
        drill_id="macro_split_push_execution",
    ),

    MacroPattern(
        id="side_lane_pressure",
        name="Side Lane Pressure",
        phase="mid",
        description=(
            "Mantener constante presencia y presión en un carril lateral "
            "para forzar al enemigo a responder, creando ventanas para "
            "tu equipo en el resto del mapa."
        ),
        when_to_apply=(
            "Cuando tu equipo está en un estado de stalemate en el mapa. "
            "Cuando el enemigo tiene peores 1v1 que tu campeón. "
            "Para crear presión antes de un objetivo mayor."
        ),
        steps=[
            "Empuja constantemente el carril lateral asignado.",
            "Mantén visión del lado del mapa donde presionas.",
            "Amenaza estructuras para forzar respuesta.",
            "Cuando responden, tu equipo actúa en el otro lado.",
        ],
        anti_pattern="Dejar de presionar para unirse a peleas sin sentido.",
        common_mistakes=[
            "Perder la oleada mientras se presiona y ceder el poke de retroceso.",
            "No coordinar con el equipo cuándo actuar.",
        ],
        applies_to_roles=["TOP", "MID"],
    ),

    MacroPattern(
        id="tempo",
        name="Tempo (Ganar Tempo)",
        phase="early_mid",
        description=(
            "Ejecutar acciones más rápido que el enemigo para crear ventanas "
            "de oportunidad. Ganar tempo significa hacer lo mismo que el enemigo "
            "pero más rápido, llegando primero al siguiente objetivo."
        ),
        when_to_apply=(
            "Después de un kill o un crash de oleada exitoso. "
            "Cuando tienes el clear más rápido en el carril. "
            "Cuando el enemigo está en base y tú no."
        ),
        steps=[
            "Ejecuta tu macro primario (push, crash, recall) más rápido que el enemigo.",
            "Llega al siguiente punto del mapa antes de que él pueda responder.",
            "Convierte el tempo en oro o estructuras antes de que se iguale.",
        ],
        anti_pattern="Desperdiciar tempo en peleas que no llevan a objetivos.",
        common_mistakes=[
            "No reconocer cuándo tienes tempo — quedarse en carril innecesariamente.",
            "Perder el tempo por una mala ruta de recall.",
        ],
        applies_to_roles=["TOP", "MID", "JNG", "ADC", "SUP"],
    ),

    MacroPattern(
        id="recall_timing",
        name="Recall Timing (Timing de Recall)",
        phase="early_mid",
        description=(
            "Hacer recall en el momento exacto donde el enemigo no puede "
            "aprovecharse de tu ausencia y tú maximizas el oro recaudado. "
            "El recall mal cronometrado es una de las mayores pérdidas de eficiencia."
        ),
        when_to_apply=(
            "Después de un crash de oleada con la siguiente oleada lejos. "
            "Después de que el enemigo va a base (recall espejado). "
            "Cuando tu oleada está en la torre enemiga y el enemigo tampoco está en carril. "
            "Cuando estás bajo de vida y el recall tiene valor defensivo."
        ),
        steps=[
            "Crash la oleada a la torre enemiga.",
            "Comprueba que el enemigo también está en base o en recall.",
            "Inicia el recall en un lugar seguro con visión.",
            "Compra los ítems planeados y vuelve antes de perder farm.",
        ],
        anti_pattern=(
            "Hacer recall con la oleada en tu torre — perdes farm y debes defender al volver."
        ),
        common_mistakes=[
            "Hacer recall cuando la oleada está en la mitad del carril.",
            "No comprar los ítems correctos en el recall.",
            "Volver tarde y perder la oleada siguiente.",
        ],
        applies_to_roles=["TOP", "MID", "ADC", "JNG"],
        drill_id="macro_recall_timing",
    ),

    MacroPattern(
        id="rotation",
        name="Rotation (Rotación)",
        phase="mid",
        description=(
            "Mover de tu carril principal a otro carril para crear una ventaja "
            "numérica temporal. Las rotaciones efectivas resultan en kills, "
            "objetivos o estructuras antes de que el enemigo pueda responder."
        ),
        when_to_apply=(
            "Cuando tienes ventaja en tu propio carril y el enemigo no puede rotar también. "
            "Cuando hay un objetivo seguro en el río. "
            "Cuando otro carril del equipo tiene ventaja y necesita convertirla en estructuras. "
            "Cuando tienes TP y el enemigo no."
        ),
        steps=[
            "Primero: crashea tu oleada antes de rotar.",
            "Usa el camino más rápido con visión asegurada.",
            "Llega al carril objetivo antes de que el enemigo pueda responder.",
            "Crea la ventaja numérica y ciérrala en objetivo o estructura.",
            "Vuelve a tu carril o al siguiente punto de valor.",
        ],
        anti_pattern="Rotar sin crashear tu oleada — pierdes farm y el enemigo puede free push.",
        common_mistakes=[
            "Rotar lento — llegar cuando el enemigo también está ahí.",
            "No tener visión del camino de rotación.",
            "Rotar cuando tu propio carril va a perder estructuras.",
            "Aceptar una pelea de baja probabilidad al rotar.",
        ],
        applies_to_roles=["MID", "JNG", "SUP"],
        drill_id="macro_rotation_with_crash",
    ),

    MacroPattern(
        id="cross_map",
        name="Cross Map (Presión Cruzada)",
        phase="mid_late",
        description=(
            "Crear presión simultánea en ambos lados del mapa para que el enemigo "
            "no pueda responder a todo a la vez. Requiere coordinación de equipo."
        ),
        when_to_apply=(
            "Cuando tu equipo tiene campeones que pueden presionar dos carriles a la vez. "
            "Cuando el enemigo tiene baja movilidad de mapa (sin TP, sin rotaciones rápidas). "
            "Post-inhibidor para crear dilemas de defensa."
        ),
        steps=[
            "Uno o dos jugadores en top presionando.",
            "El resto del equipo amenazando mid/bot o un objetivo.",
            "El enemigo no puede responder a ambos — cede terreno en uno.",
        ],
        anti_pattern="Agruparse cuando tienes presión cruzada activa.",
        common_mistakes=[
            "No coordinar quién presiona qué lado.",
            "Aceptar teamfight cuando el cross map está generando oro.",
        ],
        applies_to_roles=["TOP", "MID", "ADC", "SUP"],
    ),

    MacroPattern(
        id="pressure_objective",
        name="Objective Pressure (Presión de Objetivo)",
        phase="mid_late",
        description=(
            "Crear presión en un objetivo (Baron, Dragon) para forzar un teamfight "
            "en condiciones favorables o conseguir el objetivo gratis si el enemigo no viene."
        ),
        when_to_apply=(
            "Cuando tienes ventaja de oro o visión superior. "
            "Cuando un objetivo está a punto de aparecer. "
            "Cuando mataste un campeón clave enemigo."
        ),
        steps=[
            "Establece visión alrededor del objetivo.",
            "Agrupa tu equipo con ventaja (número, vida, maná).",
            "Amenaza iniciar el objetivo.",
            "Si el enemigo viene: pelea con la ventaja; si no viene: consigue el objetivo.",
        ],
        anti_pattern="Buscar peleas aleatorias antes de establecer el control del objetivo.",
        common_mistakes=[
            "No tener visión antes de amenazar el objetivo.",
            "Empezar el objetivo cuando el enemigo puede contestarlo.",
            "Pelear lejos del objetivo (el enemigo puede steal).",
        ],
        applies_to_roles=["TOP", "MID", "JNG", "ADC", "SUP"],
        drill_id="macro_objective_pressure",
    ),

    MacroPattern(
        id="teamfight_setup",
        name="Teamfight Setup (Preparar Pelea)",
        phase="mid_late",
        description=(
            "Posicionarse, usar habilidades de control, y entrar a la pelea "
            "en el momento y posición óptimos para maximizar el daño o el CC."
        ),
        when_to_apply=(
            "Cuando el equipo enemigo está desposicionado. "
            "Cuando todos tus cooldowns están disponibles. "
            "En peleas alrededor de objetivos mayores."
        ),
        steps=[
            "Establece visión y flanqueo si es tu rol.",
            "Espera la habilidad key del enemigo antes de entrar.",
            "Entra en el ángulo que maximiza tu impacto según tu rol.",
            "Prioriza los targets más peligrosos según tu campeón.",
        ],
        anti_pattern="Entrar a la pelea sin un ángulo claro o cuando el enemigo espera.",
        common_mistakes=[
            "Entrar demasiado pronto y morir antes de usar habilidades.",
            "Atacar al target equivocado según tu kit.",
            "Luchar sobre el objetivo en lugar de junto al objetivo.",
        ],
        applies_to_roles=["TOP", "MID", "JNG", "ADC", "SUP"],
        drill_id="macro_teamfight_positioning",
    ),

    MacroPattern(
        id="siege",
        name="Siege (Asedio)",
        phase="mid_late",
        description=(
            "Atacar una torre defensiva de forma sostenida mientras se mantiene "
            "el control de zona para evitar que el enemigo rompa el asedio."
        ),
        when_to_apply=(
            "Cuando tienes el control de visión del área. "
            "Cuando tienes composición con rango o poke. "
            "Cuando el enemigo no puede pelear en campo abierto."
        ),
        steps=[
            "Establece visión ofensiva alrededor de la estructura objetivo.",
            "Posiciónate con rango superior al enemigo.",
            "Usa poke para debilitarlos antes de que puedan contestar.",
            "Avanza cuando el enemigo se retira bajo torre.",
        ],
        anti_pattern="Avanzar sin visión y ser flanqueado por el equipo enemigo.",
        common_mistakes=[
            "No mantener control de visión durante el asedio.",
            "Entrar demasiado cerca de la torre bajo presión.",
            "No respetar el engage del equipo enemigo.",
        ],
        applies_to_roles=["MID", "ADC", "SUP", "TOP"],
    ),
]

PATTERNS_BY_ID: dict[str, MacroPattern] = {p.id: p for p in PATTERNS}
