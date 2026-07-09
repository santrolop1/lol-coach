"""
Páginas de runas meta para top lane y carriles de combate.
Los perfiles de campeón referencian estas páginas por ID.
"""

from backend.game_intelligence.models.rune import RunePage

PAGES: list[RunePage] = [
    RunePage(
        id="conqueror_standard",
        name="Conqueror Standard",
        primary_tree="precision",
        primary_keystone="conqueror",
        primary_slots=["triumph", "legend_alacrity", "last_stand"],
        secondary_tree="resolve",
        secondary_slots=["bone_plating", "unflinching"],
        shards=["adaptive", "adaptive", "armor"],
        when_to_use=(
            "Luchadores en peleas largas y sostenidas. "
            "Estándar para Darius, Irelia, Garen, Fiora, Camille."
        ),
        description=(
            "Conqueror apila en peleas largas y da sanación al máximo. "
            "Triumph da sustain post-kill. Legend Alacrity da velocidad de ataque. "
            "Last Stand potencia cuando estás bajo de vida."
        ),
        patch_version="14.12",
    ),
    RunePage(
        id="lethal_tempo_crit",
        name="Lethal Tempo Crit",
        primary_tree="precision",
        primary_keystone="lethal_tempo",
        primary_slots=["triumph", "legend_alacrity", "coup_de_grace"],
        secondary_tree="resolve",
        secondary_slots=["bone_plating", "unflinching"],
        shards=["adaptive", "adaptive", "armor"],
        when_to_use=(
            "Campeones con alta velocidad de ataque y crit que necesitan rampear. "
            "Óptimo para Tryndamere top lane estándar."
        ),
        description=(
            "Lethal Tempo da velocidad de ataque al rampear — perfecto para "
            "campeones que atacan rápido como Tryndamere. "
            "Coup de Grace amplifica el daño a targets bajos de vida."
        ),
        patch_version="14.12",
    ),
    RunePage(
        id="tryndamere_grasp",
        name="Tryndamere Grasp (vs Poke/Peel)",
        primary_tree="resolve",
        primary_keystone="grasp_of_the_undying",
        primary_slots=["shield_bash", "bone_plating", "unflinching"],
        secondary_tree="precision",
        secondary_slots=["triumph", "legend_alacrity"],
        shards=["adaptive", "armor", "hp_scaling"],
        when_to_use=(
            "Contra poke pesado en carril (Kennen, Jayce, Teemo). "
            "Cuando necesitas más sustain en lane en lugar de daño."
        ),
        description=(
            "Grasp da HP permanente y sanación en cada proc. "
            "Bone Plating reduce el poke. Shield Bash potencia el engage con W. "
            "Pérdida de daño vs Lethal Tempo, ganancia de supervivencia en lane."
        ),
        patch_version="14.12",
    ),
    RunePage(
        id="grasp_tank",
        name="Grasp Tank Standard",
        primary_tree="resolve",
        primary_keystone="grasp_of_the_undying",
        primary_slots=["font_of_life", "conditioning", "overgrowth"],
        secondary_tree="inspiration",
        secondary_slots=["biscuit_delivery", "time_warp_tonic"],
        shards=["hp_scaling", "armor", "mr"],
        when_to_use=(
            "Tanks puros (Malphite, Ornn, Cho'Gath). "
            "Cuando el objetivo es ser indestructible, no hacer daño."
        ),
        description=(
            "Grasp + Overgrowth hacen crecer el HP exponencialmente. "
            "Conditioning da armor y MR pasivo tarde. "
            "Font of Life da healing al equipo para utility extra."
        ),
        patch_version="14.12",
    ),
    RunePage(
        id="press_the_attack",
        name="Press the Attack (Duelist)",
        primary_tree="precision",
        primary_keystone="press_the_attack",
        primary_slots=["triumph", "legend_alacrity", "coup_de_grace"],
        secondary_tree="domination",
        secondary_slots=["taste_of_blood", "ravenous_hunter"],
        shards=["adaptive", "adaptive", "armor"],
        when_to_use=(
            "Duelistas con hit-pattern rápido que quieren burst inmediato. "
            "Fiora, Camille, o cuando quieres una pelea de 3 básicos."
        ),
        description=(
            "PTA aplica vulnerabilidad al enemigo en 3 básicos — máximo daño de pelea corta. "
            "Taste of Blood y Ravenous Hunter dan sustain extra."
        ),
        patch_version="14.12",
    ),
    RunePage(
        id="phase_rush_poke",
        name="Phase Rush (Poke/Kite)",
        primary_tree="sorcery",
        primary_keystone="phase_rush",
        primary_slots=["manaflow_band", "transcendence", "gathering_storm"],
        secondary_tree="inspiration",
        secondary_slots=["biscuit_delivery", "cosmic_insight"],
        shards=["adaptive", "adaptive", "armor"],
        when_to_use=(
            "Campeones de poke que necesitan escape o kite (Teemo, Kennen). "
            "Cuando el objetivo es nunca ser atrapado."
        ),
        description=(
            "Phase Rush da velocidad de movimiento masiva después de un combo. "
            "Gathering Storm escala con el tiempo para late game power. "
            "Biscuits dan sustain de maná en lane."
        ),
        patch_version="14.12",
    ),
    RunePage(
        id="electrocute_assassin",
        name="Electrocute (Assassin/Burst)",
        primary_tree="domination",
        primary_keystone="electrocute",
        primary_slots=["sudden_impact", "eyeball_collection", "treasure_hunter"],
        secondary_tree="sorcery",
        secondary_slots=["celerity", "waterwalking"],
        shards=["adaptive", "adaptive", "armor"],
        when_to_use=(
            "Campeones de burst que quieren one-shot en 3 habilidades. "
            "Renekton early dominance, Pantheon, o poke de alta potencia."
        ),
        description=(
            "Electrocute hace el combo de 3 habilidades extremadamente poderoso early. "
            "Sudden Impact amplifica el daño post-dash. "
            "Treasure Hunter da gold extra por first bloods."
        ),
        patch_version="14.12",
    ),
    RunePage(
        id="fleet_footwork",
        name="Fleet Footwork (Sustain Lane)",
        primary_tree="precision",
        primary_keystone="fleet_footwork",
        primary_slots=["presence_of_mind", "legend_alacrity", "coup_de_grace"],
        secondary_tree="resolve",
        secondary_slots=["second_wind", "unflinching"],
        shards=["adaptive", "adaptive", "hp_scaling"],
        when_to_use=(
            "Cuando la fase de lane es muy difícil y necesitas sustain. "
            "Campeones sin sustain propio contra poke pesado."
        ),
        description=(
            "Fleet da sanación en básicos empoderados. "
            "Second Wind da regen pasiva de HP. "
            "Sacrifice de daño por supervivencia en lane."
        ),
        patch_version="14.12",
    ),
]

PAGES_BY_ID: dict[str, RunePage] = {p.id: p for p in PAGES}
