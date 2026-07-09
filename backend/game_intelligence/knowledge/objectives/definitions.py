"""
Biblioteca universal de objetivos del mapa.
"""

from backend.game_intelligence.models.objective import (
    ObjectiveDefinition, ObjectiveTiming, ObjectiveType, DragonType, Priority,
)

OBJECTIVES: list[ObjectiveDefinition] = [
    # ── Barón Nashor ─────────────────────────────────────────────────────────
    ObjectiveDefinition(
        id="baron",
        name="Barón Nashor",
        type=ObjectiveType.BARON,
        priority=Priority.CRITICAL,
        description=(
            "El objetivo más poderoso del juego. El buff de Barón mejora "
            "las tropas del equipo y otorga estadísticas temporales. "
            "Generalmente cierra el juego si se ejecuta correctamente."
        ),
        reward=(
            "Hand of Baron: mejora las tropas de todos los carriles. "
            "Equipos sin inhibidores caídos pueden ganar el juego solo con esto."
        ),
        timing=ObjectiveTiming(
            spawn_minutes=20.0,
            respawn_minutes=6.0,
            ideal_attempt_window=(
                "Después de un teamfight ganado con 2+ kills enemigos. "
                "Cuando el carry enemigo está muerto o en base."
            ),
            warning=(
                "NUNCA intentar Baron con el equipo enemigo vivo y en el mapa. "
                "NUNCA intentar Baron con el equipo en mal estado de HP/maná."
            ),
        ),
        requirements=[
            "Mínimo 1 enemigo muerto o en base con recall.",
            "Control de visión del pit (wards dentro y en entradas).",
            "Equipo con vida y maná para la pelea post-Baron.",
            "Preferiblemente al menos 2 enemies muertos.",
        ],
        risks=[
            "Baron steal con smite — siempre es posible.",
            "Contestación de 5v5 desfavorable si el equipo no está listo.",
            "Quedar bajo de vida durante Baron y morir en la pelea que sigue.",
        ],
        tips=[
            "Controla el Baron desde fuera del pit — no entres sin visión.",
            "El Baron empoderado tarda 20s en aplicarse a las tropas.",
            "El buff de Baron dura 3 minutos — úsalo para presionar todos los carriles.",
            "Después de Baron: split push o macro grupal, no pelear sin necesidad.",
        ],
        common_mistakes=[
            "Intentar Baron sin visión y ser contestados.",
            "No convertir el Baron en estructuras — el buff expira.",
            "Pelear innecesariamente con el buff activo.",
        ],
        role_responsibility={
            "JNG": "Smite al Baron. Inicia el Baron cuando el team lo indica.",
            "TOP": "Tankea el Baron. Visión de la entrada superior.",
            "MID": "Visión central. Listo para luchar si el enemigo contesta.",
            "ADC": "DPS al Baron. Posición segura fuera del pit.",
            "SUP": "Visión de todas las entradas. Control wards.",
        },
    ),

    # ── Heraldo del Abismo ────────────────────────────────────────────────────
    ObjectiveDefinition(
        id="herald",
        name="Heraldo del Abismo",
        type=ObjectiveType.HERALD,
        priority=Priority.HIGH,
        description=(
            "Objetivo early que al ser soltado como ítem puede destruir "
            "una torre en segundos. Permite hacer snowball de estructuras early."
        ),
        reward=(
            "Ojo del Heraldo: Ítem que al usarse invoca al Heraldo para destrozar una torre. "
            "Puede tomar una primera o segunda torre fácilmente."
        ),
        timing=ObjectiveTiming(
            spawn_minutes=8.0,
            respawn_minutes=None,
            ideal_attempt_window=(
                "Entre minuto 8 y 13 cuando aparece. "
                "Inmediatamente después de ganarlo, usarlo en la primera torre disponible."
            ),
            warning=(
                "Desaparece al minuto 13:45. No dejar expirar. "
                "El segundo Heraldo spawna solo si el primero es tomado antes del min 13:45."
            ),
        ),
        requirements=[
            "Control del río del lado del Herald.",
            "Ventaja numérica o enemigo en base.",
            "Jungla con HP suficiente para pelear Herald.",
        ],
        risks=[
            "Perder el 2v2 o 3v3 en el intento.",
            "Contención del Herald por el enemigo.",
        ],
        tips=[
            "El primer Heraldo: usarlo para primera torre top o mid.",
            "El segundo Heraldo (si consigues el primero): segunda torre del mismo carril.",
            "Doble Heraldo en el mismo carril puede dar inhibidor antes del min 20.",
        ],
        common_mistakes=[
            "Dejar expirar el Herald por no usarlo a tiempo.",
            "Usarlo en una torre ya con pocas HP — el valor está en torretas llenas.",
        ],
        role_responsibility={
            "JNG": "Control y smite del Herald.",
            "TOP": "Ayudar en el Herald del lado top. Recibir el ítem si está en top.",
        },
    ),

    # ── Dragones ─────────────────────────────────────────────────────────────
    ObjectiveDefinition(
        id="dragon_soul",
        name="Dragon Soul (4 Dragones)",
        type=ObjectiveType.DRAGON,
        priority=Priority.CRITICAL,
        description=(
            "Al conseguir 4 dragones del mismo tipo, el equipo obtiene el Dragon Soul, "
            "un buff permanente extremadamente poderoso que puede definir el juego."
        ),
        reward=(
            "Dragon Soul: buff permanente variado según tipo de dragón. "
            "Infernal: daño AoE explosivo. Mountain: escudo en combate. "
            "Ocean: regen fuera de combate. Cloud: movimiento aumentado. "
            "Hextech: lento de cadena en básicos. Chemtech: resucitar con stats temporales."
        ),
        timing=ObjectiveTiming(
            spawn_minutes=5.0,
            respawn_minutes=5.0,
            ideal_attempt_window=(
                "Cada vez que spawna. No dejar pasar dragones sin intentarlos. "
                "El soul generalmente define quién gana post-mid game."
            ),
            warning="No perder el 4to dragón enemigo — puede revertir el juego.",
        ),
        requirements=[
            "Prioridad de bot lane para facilitar la visión del dragón.",
            "Control de visión del pit.",
            "Jungla lista para smite.",
        ],
        risks=[
            "El equipo enemigo contesta con ventaja numérica.",
            "Baron aparece al minuto 20 — elegir entre dragon y baron.",
        ],
        tips=[
            "Priorizar dragones del mismo tipo para el soul.",
            "Controlar el carril bot ayuda a controlar el Dragon.",
            "El último dragón para el soul vale más que un Baron.",
        ],
        common_mistakes=[
            "No ir al dragón cuando spawna por estar en carril.",
            "No tener visión antes de iniciar.",
        ],
        role_responsibility={
            "JNG": "Smite. Controla el timing del dragón.",
            "BOT": "Ganar/freezar carril para tener prioridad de dragón.",
            "SUP": "Wards del pit y entradas.",
        },
    ),

    # ── Torres ────────────────────────────────────────────────────────────────
    ObjectiveDefinition(
        id="first_tower",
        name="Primera Torre (First Tower)",
        type=ObjectiveType.TOWER,
        priority=Priority.HIGH,
        description=(
            "Tomar la primera torre de un carril abre el mapa, da un bono de oro "
            "significativo al equipo, y permite acceso a la base enemiga."
        ),
        reward=(
            "Bono de oro: 150g al team + 150g extra al primer jugador en dañarla. "
            "Apertura del mapa para roaming y presión."
        ),
        timing=ObjectiveTiming(
            spawn_minutes=0.0,
            ideal_attempt_window=(
                "Tras ganar un 1v1 o crash de oleada exitoso antes del min 14. "
                "El bono first tower solo aplica a la primera torre global."
            ),
            warning="No sobreextender para tomar torre sin visión.",
        ),
        requirements=[
            "Oleada grande o heraldo empujando.",
            "Visión del área.",
            "Enemigo fuera de posición o muerto.",
        ],
        risks=[
            "Jungla enemiga puede contestar durante el push.",
            "TP enemigo puede responder.",
        ],
        tips=[
            "El bono first tower se divide entre todos los que hacen daño.",
            "Una torre tomada temprano acelera toda la economía del equipo.",
        ],
        common_mistakes=[
            "Dejar la torre al 20% de vida y no terminarla.",
            "Tomar la torre sin plan de escapar si el enemigo responde.",
        ],
        role_responsibility={
            "TOP": "Primera torre top mediante split push o ventaja de carril.",
            "MID": "Rotar para ayudar en primera torre de carriles adyacentes.",
        },
    ),
    ObjectiveDefinition(
        id="inhibitor",
        name="Inhibidor",
        type=ObjectiveType.INHIBITOR,
        priority=Priority.HIGH,
        description=(
            "Destruir un inhibidor hace que las tropas del equipo en ese carril "
            "incluyan Super Troops extremadamente poderosas durante 5 minutos."
        ),
        reward=(
            "Super Minions en el carril correspondiente por 5 minutos. "
            "El equipo puede presionar todos los carriles con ventaja de tropas."
        ),
        timing=ObjectiveTiming(
            respawn_minutes=5.0,
            ideal_attempt_window=(
                "Cuando tienes ventaja de Baron o una ventaja masiva de teamfight. "
                "Después de tomar ambas torres de un carril."
            ),
            warning="El inhibidor respawnea a los 5 minutos — convertir la ventaja en victorias de carril.",
        ),
        requirements=[
            "Acceso al inhibidor (ambas torres del carril caídas).",
            "Ventaja numérica o buff activo (Baron).",
        ],
        risks=["Defender el resto del mapa durante el push de inhibidor."],
        tips=[
            "Inhibidor caído + Baron = win condition casi garantizada.",
            "Con Super Minions, divide y conquistarás más fácilmente.",
        ],
        common_mistakes=[
            "No convertir el inhibidor caído en win inmediata.",
            "Luchar en el mapa cuando los Super Minions pueden hacer el trabajo.",
        ],
        role_responsibility={
            "ALL": "Push del carril con inhibidor caído. No perder el tiempo en fights innecesarios.",
        },
    ),
]

OBJECTIVES_BY_ID: dict[str, ObjectiveDefinition] = {o.id: o for o in OBJECTIVES}
