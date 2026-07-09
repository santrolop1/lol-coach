"""Tryndamere vs Darius — TOP."""

from backend.game_intelligence.models.matchup import MatchupProfile

MATCHUP = MatchupProfile(
    champion="tryndamere",
    enemy="darius",
    role="TOP",
    patch_version="14.12",
    difficulty="hard",
    summary=(
        "Darius gana todos los intercambios en early game. "
        "Su Q sana a stack completo y su pasiva sangra masivamente. "
        "Tryndamere debe farmear, sobrevivir, y ganar en late game cuando la R "
        "hace imposible que Darius complete su combo completo antes de ser asesinado."
    ),
    early_game=(
        "Niveles 1-5: EVITAR cualquier intercambio. Darius tiene más daño sostenido. "
        "Farmear de lejos. Si Darius usa Q: E para salir del rango exterior curativo. "
        "Usar Q para curar el daño de su pasiva gradualmente. "
        "Nivel 6 de Darius es extremadamente peligroso — preparar R antes."
    ),
    mid_game=(
        "Con primer ítem (Trinity Force): los intercambios se igualan si tienes R activa. "
        "Pushear y usar Recall Timing para maximizar el farm. "
        "Evitar peleas sin R disponible. Usar el freeze si el gankeo de Darius es peligroso."
    ),
    late_game=(
        "Con 2-3 ítems: Tryndamere gana el 1v1 si juega R correctamente. "
        "Darius no puede completar 5 stacks si la R está activa. "
        "En el split push tardío: Darius no puede alcanzarte si usas E para escapar."
    ),
    our_spikes=[
        "Nivel 6: R activa — permite sobrevivir el combo de Darius",
        "Trinity Force: primer ítem — empezar a igualar el intercambio",
        "2 ítems crit: dominar el 1v1 tardío",
    ],
    enemy_spikes=[
        "Nivel 6: Noxian Guillotine puede one-shot",
        "Nivel 1-5: dominio absoluto del carril",
        "Glacial Augment / Heartsteel completado: más difícil de matar",
    ],
    trading_style=(
        "EL PATRÓN INCORRECTO: hacer intercambios largos con Darius sin R. "
        "EL PATRÓN CORRECTO: breves basics para farmear, E para salir de su Q, "
        "solo comprometerse en intercambios cuando R está activa y cerca de base."
    ),
    wave_plan=[],  # referencias a WaveRegistry por ID si el matchup requiere plan especial
    item_priority=[],
    rune_adjustments=["Considerar Grasp si el poke de Darius es muy agresivo early."],
    tips=[
        "El objetivo NUNCA es matar a Darius en early — es sobrevivir y llegar a late.",
        "Cuando Darius use W (tira del gancho): E inmediato para salir.",
        "Mantener alta la furia antes de cada intercambio para curar más con Q.",
        "Si Darius tiene Ignite: no comprometerse en peleas al 40% de vida.",
        "Split push post-2 ítems: Darius no puede alcanzarte si guardas E.",
    ],
    common_mistakes=[
        "Intentar ganar trades en levels 1-3 — siempre pierde.",
        "No usar E para escapar del radio exterior de su Q (parte curativa).",
        "Activar R demasiado tarde cuando Darius ya tiene 5 stacks y la R ejecutora.",
        "No splitear cuando Darius no puede seguirte con E guardado.",
    ],
    drill_ids=["r_activation_timing", "deaths_lt_threshold"],
)
