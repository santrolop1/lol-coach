"""Tryndamere vs Garen — TOP."""

from backend.game_intelligence.models.matchup import MatchupProfile

MATCHUP = MatchupProfile(
    champion="tryndamere",
    enemy="garen",
    role="TOP",
    patch_version="14.12",
    difficulty="medium",
    summary=(
        "Matchup relativamente equilibrado. Garen tiene ventaja early por su silencio "
        "y su regen pasiva. Tryndamere iguala en mid game y domina en late game. "
        "El matchup se gana o pierde dependiendo de quién escala mejor "
        "con sus primeros ítems."
    ),
    early_game=(
        "Niveles 1-5: respetar el Q de Garen (silencia y da velocidad). "
        "Si Garen usa Q: no inicies un intercambio — el silencio te impide usar Q para curar. "
        "Su pasiva (regen fuera de combate) significa que los intercambios de poke no tienen efecto. "
        "Farmear y mantener la oleada equilibrada."
    ),
    mid_game=(
        "Con Trinity Force: los intercambios se vuelven favorables si evitas su Q. "
        "Aprovechar que Garen no tiene dash — usar E para kite si es necesario. "
        "Su E (Judgment/Spin) hace daño AoE — posicionarse para no recibir todo."
    ),
    late_game=(
        "Tryndamere domina el 1v1 tardío. "
        "Garen con Juggernaut/Heartsteel puede ser difícil de matar. "
        "Split push: Garen puede seguirte pero no alcanzarte con E de escape. "
        "Con R activa y full build: Tryndamere mata a Garen limpiamente."
    ),
    our_spikes=[
        "Nivel 6: R activa — sobrevivir la R de Garen (Demacian Justice)",
        "Trinity Force: ventaja de DPS sobre Garen",
        "2-3 ítems crit: dominar completamente el 1v1",
    ],
    enemy_spikes=[
        "Nivel 6: Demacian Justice (R) puede one-shot si estás muy bajo",
        "Stridebreaker completado: puede alcanzarte mejor",
        "Heartsteel: se vuelve muy difícil de matar tarde",
    ],
    trading_style=(
        "EL PATRÓN INCORRECTO: intercambiar cuando Garen tiene Q disponible. "
        "EL PATRÓN CORRECTO: esperar que use Q, entrar inmediatamente, "
        "hacer daño y salir antes de su E-spin. Con nivel 6+: comprometerse totalmente."
    ),
    wave_plan=[],
    item_priority=[
        # Si Garen construye mucho armor: adaptar a daño verdadero o Black Cleaver
    ],
    rune_adjustments=[],
    tips=[
        "El Q de Garen silencia — espera siempre a que lo use antes de entrar.",
        "Su R (Demacian Justice) solo mata si estás muy bajo. Nunca luchar por debajo del 20% sin R.",
        "Garen no tiene dash — tu E es siempre una opción de escape garantizada.",
        "Si Garen construye Heartsteel: considerar Mortal Reminder para el regen pasivo.",
    ],
    common_mistakes=[
        "No respetar el silencio de su Q — entrar a curar con Q propio justo cuando él usa el suyo.",
        "Perseguir a Garen cuando ya tiene su Q disponible.",
        "Subestimar el daño de su E (Judgment) en carril.",
        "No activar R cuando la R de Garen (Demacian Justice) está a punto de caer.",
    ],
    drill_ids=["r_activation_timing"],
)
