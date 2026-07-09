"""
Ward spots universales del mapa.
No es un catálogo exhaustivo — son los spots más importantes y sus patrones.
"""

from backend.game_intelligence.models.vision import WardSpot, WardType, VisionZone, VisionPurpose

WARD_SPOTS: list[WardSpot] = [
    WardSpot(
        id="baron_entrance_top",
        name="Entrada superior de Barón",
        zone=VisionZone.BARON_PIT,
        ward_type=WardType.STEALTH,
        purpose=VisionPurpose.OBJECTIVE,
        description="Spot que cubre la entrada superior al pit de Barón desde el carril top.",
        when_to_use="Antes de cualquier intento de Barón o cuando el enemigo podría contestarlo.",
        map_position="Bush entre el carril top y el Baron pit, entrada norte.",
        timing_minutes=[19.0, 20.0, 26.0, 32.0],
        role_priority=["JNG", "SUP", "TOP"],
        tips=["Este ward avisa del flanco del top laner enemigo durante el Baron."],
    ),
    WardSpot(
        id="baron_entrance_mid",
        name="Entrada lateral de Barón (mid)",
        zone=VisionZone.BARON_PIT,
        ward_type=WardType.STEALTH,
        purpose=VisionPurpose.OBJECTIVE,
        description="Spot que cubre la entrada al Baron desde el carril mid.",
        when_to_use="Cuando el enemigo puede contestar el Baron por el mid.",
        map_position="Entre mid lane y el Baron pit, entrada este.",
        timing_minutes=[19.0, 20.0],
        role_priority=["SUP", "JNG"],
    ),
    WardSpot(
        id="baron_control_ward",
        name="Control Ward dentro del Baron Pit",
        zone=VisionZone.BARON_PIT,
        ward_type=WardType.CONTROL,
        purpose=VisionPurpose.OBJECTIVE,
        description="Control ward dentro del pit para ver smite del jungla enemigo.",
        when_to_use="Cuando el Baron está a 2+ minutos. Crítico antes del Baron.",
        map_position="Dentro del pit de Barón.",
        timing_minutes=[18.0, 19.0],
        requires_deep_entry=True,
        role_priority=["SUP", "JNG"],
        tips=["El control ward dentro revela al jungla enemigo intentando robar con smite."],
    ),
    WardSpot(
        id="dragon_entrance_bot",
        name="Entrada bot de Dragón",
        zone=VisionZone.DRAGON_PIT,
        ward_type=WardType.STEALTH,
        purpose=VisionPurpose.OBJECTIVE,
        description="Cubre la entrada al Dragon desde el carril bot.",
        when_to_use="Cada vez que el dragón va a spawnear o está en respawn.",
        map_position="Bush al norte del Dragon pit, entrada desde bot lane.",
        timing_minutes=[4.5, 9.5, 14.5, 19.5],
        role_priority=["SUP", "JNG", "ADC"],
        tips=["Colocar antes de los 4:30 para el primer dragón del juego."],
    ),
    WardSpot(
        id="dragon_control_ward",
        name="Control Ward en el Dragon Pit",
        zone=VisionZone.DRAGON_PIT,
        ward_type=WardType.CONTROL,
        purpose=VisionPurpose.OBJECTIVE,
        description="Control ward dentro del pit de dragón.",
        when_to_use="Antes de cada intento de dragón para visión garantizada.",
        map_position="Dentro del pit de Dragón.",
        timing_minutes=[4.0, 9.0, 14.0],
        requires_deep_entry=True,
        role_priority=["SUP"],
    ),
    WardSpot(
        id="river_top_tribrush",
        name="Tribrush superior del río",
        zone=VisionZone.RIVER_TOP,
        ward_type=WardType.STEALTH,
        purpose=VisionPurpose.DEFENSIVE,
        description="Cubre el río superior para detectar ganks al top laner.",
        when_to_use=(
            "Top laner sin flash o en situación de ventaja donde el enemigo puede gankear. "
            "Estándar cuando tu carril está empujado."
        ),
        map_position="Tribrush del río, lado superior del mapa.",
        timing_minutes=[2.0, 5.0, 8.0, 11.0],
        role_priority=["TOP", "JNG", "SUP"],
        tips=["Si estás empujado sin este ward, asumes el riesgo de gank."],
    ),
    WardSpot(
        id="river_bot_tribrush",
        name="Tribrush inferior del río",
        zone=VisionZone.RIVER_BOT,
        ward_type=WardType.STEALTH,
        purpose=VisionPurpose.DEFENSIVE,
        description="Cubre el río inferior para detectar ganks al ADC/Support.",
        when_to_use=(
            "Siempre que el carril bot está empujado o el jungla enemigo pudo estar bottom."
        ),
        map_position="Tribrush del río, lado inferior del mapa.",
        timing_minutes=[2.0, 4.5, 7.0, 9.5],
        role_priority=["SUP", "ADC"],
        tips=["Prioridad del support — colocar antes de empujar la oleada."],
    ),
    WardSpot(
        id="enemy_jungle_blue",
        name="Ward Jungla Enemiga (Blue side)",
        zone=VisionZone.ENEMY_JUNGLE,
        ward_type=WardType.STEALTH,
        purpose=VisionPurpose.OFFENSIVE,
        description="Ward en la jungla enemiga para trackear al jungla contrario.",
        when_to_use=(
            "Cuando tienes ventaja numérica suficiente para entrar a la jungla enemiga. "
            "Después de objectivos para anticipar la ruta del jungla."
        ),
        map_position="Tribrush o entrada lateral de la jungla enemiga.",
        timing_minutes=[6.0, 10.0, 15.0],
        requires_deep_entry=True,
        role_priority=["JNG", "SUP", "MID"],
        tips=["Un ward de jungla enemiga vale más que 5 wards en tu base."],
    ),
    WardSpot(
        id="pixel_bush_bot",
        name="Pixel Bush (Bot)",
        zone=VisionZone.RIVER_BOT,
        ward_type=WardType.STEALTH,
        purpose=VisionPurpose.DEFENSIVE,
        description="El spot más importante de bot lane — cubre el río y el carril.",
        when_to_use=(
            "Siempre que sea posible en bot lane. "
            "Da visión del río y avisa ganks antes de que lleguen al carril."
        ),
        map_position="Pixel bush adyacente al río en bot lane.",
        timing_minutes=[1.5, 5.0, 8.5],
        role_priority=["SUP"],
        tips=["Este ward a minuto 1:30 puede prevenir un invade o gank level 2."],
    ),
]

WARD_SPOTS_BY_ID: dict[str, WardSpot] = {w.id: w for w in WARD_SPOTS}
