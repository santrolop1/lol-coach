"""
Builds de ejemplo para top laners comunes.
Los perfiles de campeón referencian ItemBuild por ID.
"""

from backend.game_intelligence.models.item import ItemBuild, BuildPath

BUILDS: list[ItemBuild] = [
    ItemBuild(
        id="tryndamere_standard_crit",
        name="Tryndamere — Crit Standard",
        description="Build de crit estándar para split push y late game carry.",
        when_to_use="Partidas normales donde llegas a late game con gracia.",
        starter=["long_sword", "health_potions"],
        core=["trinity_force", "phantom_dancer", "infinity_edge"],
        situational=["ravenous_hydra", "guardian_angel", "mortal_reminder", "deaths_dance", "steraks_gage", "wit_s_end"],
        boots_options=["plated_steelcaps", "mercury_treads"],
        stat_priority=["crit", "ad", "as", "hp"],
        patch_version="14.12",
    ),
    ItemBuild(
        id="tryndamere_vs_tanks",
        name="Tryndamere — vs Tanks",
        description="Adaptación con Kraken Slayer contra frontlines pesadas.",
        when_to_use="Cuando el equipo enemigo tiene 2+ tanks o mucho HP.",
        starter=["long_sword", "health_potions"],
        core=["kraken_slayer", "phantom_dancer", "infinity_edge"],
        situational=["mortal_reminder", "guardian_angel", "wit_s_end"],
        boots_options=["plated_steelcaps", "mercury_treads"],
        stat_priority=["crit", "as", "ad"],
        patch_version="14.12",
    ),
    ItemBuild(
        id="tryndamere_vs_poke",
        name="Tryndamere — vs Poke",
        description="Build con Spirit Visage y Steraks para aguantar poke mágico.",
        when_to_use="Contra llaneros con mucho poke (Kennen, Jayce, Teemo AP).",
        starter=["long_sword", "health_potions"],
        core=["trinity_force", "spirit_visage", "phantom_dancer"],
        situational=["steraks_gage", "wit_s_end", "guardian_angel"],
        boots_options=["mercury_treads"],
        stat_priority=["hp", "mr", "crit", "ad"],
        patch_version="14.12",
    ),
    ItemBuild(
        id="darius_standard",
        name="Darius — Standard Fighter",
        description="Build de luchador pesado para dominancia temprana y teamfight.",
        when_to_use="Partidas donde puedes ganar la fase de carriles y hacer snowball.",
        starter=["dorans_shield", "health_potions"],
        core=["trinity_force", "steraks_gage", "deaths_dance"],
        situational=["black_cleaver", "spirit_visage", "thornmail", "warmogs_armor"],
        boots_options=["plated_steelcaps", "mercury_treads"],
        stat_priority=["hp", "ad", "cdr"],
        patch_version="14.12",
    ),
    ItemBuild(
        id="generic_toplaner_tank",
        name="Generic Tank Top Laner",
        description="Build genérica de tank para campeones engagers o frontlines.",
        when_to_use="En tanks puros sin necesidad de daño (Malphite, Ornn).",
        starter=["dorans_shield", "health_potions"],
        core=["heartsteel", "sunfire_aegis", "spirit_visage"],
        situational=["thornmail", "warmogs_armor", "guardian_angel"],
        boots_options=["plated_steelcaps", "mercury_treads"],
        stat_priority=["hp", "armor", "mr", "cdr"],
        patch_version="14.12",
    ),
]

BUILD_PATHS: list[BuildPath] = [
    BuildPath(
        item_id="trinity_force",
        components=["sheen", "phage", "stinger"],
        first_back_gold=1100,
        notes="Comprar Phage primero para HP y slow. Luego Sheen para el spellblade.",
    ),
    BuildPath(
        item_id="phantom_dancer",
        components=["daggers", "cloak_of_agility"],
        first_back_gold=900,
        notes="Acumular daggers para velocidad de ataque temprana.",
    ),
    BuildPath(
        item_id="heartsteel",
        components=["giants_belt", "ruby_crystal"],
        first_back_gold=800,
        notes="Comprar Giants Belt lo antes posible para la pasiva de HP.",
    ),
]

BUILDS_BY_ID: dict[str, ItemBuild] = {b.id: b for b in BUILDS}
