"""Tryndamere vs Teemo — TOP."""

from backend.game_intelligence.models.matchup import MatchupProfile

MATCHUP = MatchupProfile(
    champion="tryndamere",
    enemy="teemo",
    role="TOP",
    patch_version="14.12",
    difficulty="hard",
    summary=(
        "Teemo es probablemente el peor matchup de Tryndamere. "
        "El Blind (Q de Teemo) niega completamente los básicos de Tryndamere, "
        "haciendo que la R sea mucho menos efectiva. "
        "Su veneno hace daño continuo que dificulta curar con Q. "
        "Los shrooms hacen imposible el split push ciego."
    ),
    early_game=(
        "Niveles 1-5: imposible ganar el intercambio. "
        "Cuando Teemo use Q (Blind): PARAR de atacar inmediatamente — los básicos fallan. "
        "Farmear con E para llegar a tropas sin exponerse al poke. "
        "Comprar Vision Wards para el river y para clearar sus shrooms en el carril."
    ),
    mid_game=(
        "Comprar Oracle's Lens (trinket rosa) para clearar shrooms en el path de split. "
        "Con Trinity Force: intentar intercambios muy cortos CUANDO el Blind no está activo. "
        "Si Teemo se posiciona en el bush: no entrar sin visión."
    ),
    late_game=(
        "Con 2-3 ítems: los intercambios aún son difíciles pero manejables sin Blind activo. "
        "Splitear comprando Control Wards para limpiar shrooms del path. "
        "Con R activa y Blind no activo: Tryndamere puede matar a Teemo."
    ),
    our_spikes=[
        "Nivel 6: R activa — sobrevivir el poke acumulado",
        "Trinity Force: daño suficiente para amenazar kills sin Blind",
        "Comprar Oracle's Lens: habilitar el split push",
    ],
    enemy_spikes=[
        "Nivel 1: Blind instantáneo nivel 1 domina",
        "Nivel 6: shrooms más frecuentes en el mapa",
        "Liandry's / AP completado: veneno masivo difícil de curar",
    ],
    trading_style=(
        "EL PATRÓN INCORRECTO: atacar a Teemo con el Blind activo — los básicos fallan. "
        "EL PATRÓN CORRECTO: esperar que el Blind expire (2.5s en niveles altos), "
        "usar E para entrar inmediatamente, hacer el mayor daño posible en esa ventana."
    ),
    wave_plan=[],
    item_priority=[],
    rune_adjustments=[
        "Grasp of the Undying sobre Lethal Tempo — más sustain en el poke continuo.",
        "Second Wind en resolución para reducir el veneno.",
    ],
    tips=[
        "Cada vez que Teemo use Q: es tu ventana de 1.5-2s sin Blind. Actúa.",
        "Comprar un Control Ward cada recall — básico en este matchup.",
        "Usar E principalmente para llegar a Teemo, no para escapar.",
        "Si Teemo está bajo de vida y recorre hacia el bush: no perseguir sin Sweeper.",
        "El objetivo del split es tomar estructuras mientras Teemo farm en carril.",
    ],
    common_mistakes=[
        "Seguir atacando cuando el Blind está activo — pierdes todos los básicos.",
        "No comprar Control Wards para los shrooms.",
        "Intentar ganar el carril en lugar de minimizar pérdidas y escalar.",
        "Perseguir a Teemo dentro de su zona de shrooms sin Oracle.",
    ],
    drill_ids=["deaths_lt_threshold"],
)
