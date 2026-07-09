"""
Patrones universales de visión por fase del juego.
"""

from backend.game_intelligence.models.vision import VisionPattern, VisionPurpose

PATTERNS: list[VisionPattern] = [
    VisionPattern(
        id="early_lane_defense",
        name="Visión defensiva de early lane",
        purpose=VisionPurpose.DEFENSIVE,
        phase="early",
        description=(
            "Visión mínima necesaria para jugar el carril con seguridad "
            "contra ganks del jungla enemigo."
        ),
        ward_spot_ids=["river_top_tribrush", "river_bot_tribrush", "pixel_bush_bot"],
        steps=[
            "Colocar ward de río antes de min 2:00.",
            "Mantener visión del río activa siempre que estés empujado.",
            "Reemplazar el ward cuando expire o sea eliminado.",
            "Usar trinket (totem) para mantener cobertura continua.",
        ],
        common_mistakes=[
            "Pushear sin tener ward activo en el río.",
            "No reemplazar el ward cuando expira.",
            "Ignorar el mapa aunque el ward no avise — puede haber muerto.",
        ],
        tips=[
            "Nivel 1: ward de río es la mayor prioridad antes de que el jungla pueda gankear.",
            "Mantener el mapa en la mente — si no tienes ward, asumir que el jungla está cerca.",
        ],
    ),
    VisionPattern(
        id="pre_objective_control",
        name="Control de visión pre-objetivo",
        purpose=VisionPurpose.OBJECTIVE,
        phase="objective",
        description=(
            "Establecer visión completa alrededor de un objetivo (Baron o Dragon) "
            "antes de iniciar para evitar contestación y flancos."
        ),
        ward_spot_ids=[
            "baron_entrance_top", "baron_entrance_mid", "baron_control_ward",
            "dragon_entrance_bot", "dragon_control_ward",
        ],
        steps=[
            "2-3 minutos antes del objetivo: iniciar colocación de wards.",
            "SUP coloca control ward dentro del pit.",
            "JNG y/o TOP ward las entradas laterales.",
            "Limpiar los wards enemigos con control wards antes de iniciar.",
            "Iniciar el objetivo solo cuando todas las entradas están cubiertas.",
        ],
        common_mistakes=[
            "Iniciar el objetivo sin visión de las entradas.",
            "No limpiar wards enemigos antes de iniciar.",
            "Olvidar el control ward dentro del pit (vulnera al steal).",
        ],
        tips=[
            "El equipo que tiene más visión del objetivo suele ganarlo.",
            "Controla el tiempo — si ya tienes visión y el enemigo no, inicia pronto.",
            "El control ward dentro del Baron pit es la inversión más rentable del juego.",
        ],
    ),
    VisionPattern(
        id="offensive_jungle_tracking",
        name="Tracking ofensivo del jungla",
        purpose=VisionPurpose.TRACKING,
        phase="mid",
        description=(
            "Visión dentro de la jungla enemiga para saber la posición del jungla "
            "contrario y permitir plays en cualquier carril."
        ),
        ward_spot_ids=["enemy_jungle_blue"],
        steps=[
            "Cuando estés con ventaja y seguro: entra a colocar ward en jungla enemiga.",
            "Comunica la posición del jungla cuando lo veas en el ward.",
            "Usa la información para permitir plays a tus llaners.",
            "Renueva el ward cuando expire (3 min).",
        ],
        common_mistakes=[
            "Entrar a wardear la jungla enemiga sin ventaja — peligroso.",
            "No comunicar la información del ward al equipo.",
        ],
        tips=[
            "Un ward de jungla enemiga cambia completamente la toma de decisiones del equipo.",
            "El mejor momento para entrarse: después de un objetivo seguro.",
        ],
    ),
]

PATTERNS_BY_ID: dict[str, VisionPattern] = {p.id: p for p in PATTERNS}
