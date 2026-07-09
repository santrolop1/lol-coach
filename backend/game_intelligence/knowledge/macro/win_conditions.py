"""
Condiciones de victoria universales del juego.
Los perfiles de campeón referencian estas por ID.
"""

from backend.game_intelligence.models.macro import WinCondition

WIN_CONDITIONS: list[WinCondition] = [
    WinCondition(
        id="split_and_win",
        name="Split Push y Ganar",
        description=(
            "Ganar el juego mediante presión constante en carril lateral, "
            "tomando estructuras mientras el equipo desvía la atención."
        ),
        required_conditions=[
            "Ventaja de 1v1 o 1v2 en el campeón.",
            "Composición del equipo que puede amenazar el otro lado.",
            "Capacidad de escapar si el enemigo rota masivamente.",
        ],
        champion_archetypes=["fighter", "bruiser", "splitpusher", "diver"],
        macro_steps=[
            "Ganar o sobrevivir la fase de carriles.",
            "Escalar a un estado de 1v1 dominante (ítems, niveles).",
            "Establecer split push en carril lateral.",
            "Coordinar con equipo para actuar cuando 2+ enemigos roten.",
            "Convertir la ventaja en estructuras o Nexus.",
        ],
        failure_modes=[
            "Morir en el split sin visión — reversa completa del ritmo.",
            "Equipo haciendo peleas 4v5 en lugar de amenazar el otro lado.",
            "Enemigo tiene mejor 1v1 y puede matarte en el split.",
        ],
    ),

    WinCondition(
        id="teamfight_and_win",
        name="Ganar Teamfights",
        description=(
            "Ganar el juego dominando peleas grupales alrededor de objetivos. "
            "Requiere composición con ventaja de pelea y uso correcto de habilidades."
        ),
        required_conditions=[
            "Composición con ventaja de teamfight (AoE, CC, engage).",
            "Correcta ejecución del timing de entrada en pelea.",
            "Control de visión para no ser flanqueados.",
        ],
        champion_archetypes=["tank", "engage", "apc", "adc", "support"],
        macro_steps=[
            "Construir ventaja de carril o sobrevivir a la fase early.",
            "Agruparse cuando los ítems de pelea están completos.",
            "Establecer control de visión alrededor del objetivo.",
            "Ejecutar teamfight con ventaja de posición.",
            "Convertir el teamfight ganado en objetivos y estructuras.",
        ],
        failure_modes=[
            "Pelear cuando el equipo enemigo tiene condiciones superiores.",
            "Entrar a la pelea con cooldowns clave en CD.",
            "No tener visión y ser flanqueados.",
        ],
    ),

    WinCondition(
        id="siege_and_win",
        name="Asediar y Ganar",
        description=(
            "Ganar lentamente el juego mediante poke y control de zona, "
            "tomando estructuras sin arriesgar una pelea directa."
        ),
        required_conditions=[
            "Composición con rango superior al enemigo.",
            "Capacidad de no morir en peleas forzadas.",
            "Acceso a wave clear para no ser diveados.",
        ],
        champion_archetypes=["poke", "artillery", "mage", "ranged_bruiser"],
        macro_steps=[
            "Sobrevivir a la fase early sin ceder ventaja.",
            "Escalar a ítems de poke/rango.",
            "Establecer asedio con control de visión.",
            "Desgastar al enemigo con poke hasta que no puedan defender.",
            "Tomar estructuras cuando el enemigo está demasiado debilitado.",
        ],
        failure_modes=[
            "El enemigo tiene dive y puede cancelar el asedio.",
            "Perder el control de visión y ser flanqueados.",
            "No tener suficiente rango para asediar con seguridad.",
        ],
    ),

    WinCondition(
        id="early_stomp",
        name="Dominar Early y Cerrar",
        description=(
            "Conseguir una ventaja abrumadora en la fase early y cerrar "
            "el juego antes de que el enemigo pueda escalar."
        ),
        required_conditions=[
            "Campeón con dominancia early (kills, CS, poke).",
            "Capacidad de rotar para extender la ventaja.",
            "Equipo capaz de convertir la ventaja en objetivos.",
        ],
        champion_archetypes=["early_dominant", "snowball", "assassin", "early_fighter"],
        macro_steps=[
            "Dominar el carril en los primeros 10 minutos.",
            "Convertir la ventaja en oro, torres, y objetivos.",
            "Rotar para extender la ventaja a otros carriles.",
            "Cerrar el juego antes del minuto 25-30.",
        ],
        failure_modes=[
            "No cerrar el juego a tiempo — el enemigo escala.",
            "Cometer errores de macro post-ventaja (irse al split sin coordinación).",
            "El enemigo tiene late-game dominante y escala.",
        ],
    ),
]

WIN_CONDITIONS_BY_ID: dict[str, WinCondition] = {w.id: w for w in WIN_CONDITIONS}
