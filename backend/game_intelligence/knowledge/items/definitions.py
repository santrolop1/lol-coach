"""
Muestra representativa de items de League of Legends.

~20 items clave para top lane / luchadores / carries.
Los builds de campeón referencian estos items por ID.

Nota: ItemDefinition.stats es list[str] — descripción de estadísticas.
"""

from backend.game_intelligence.models.item import ItemDefinition

ITEMS: list[ItemDefinition] = [
    # ── Míticos ──────────────────────────────────────────────────────────────
    ItemDefinition(
        id="trinity_force",
        name="Trinity Force",
        cost=3333,
        description=(
            "Ítem mítico para luchadores que se benefician de básicos potenciados. "
            "Spellblade en habilidades. Excelente en split pushers con combos rápidos."
        ),
        stats=["30 AD", "30% AS", "200 HP", "20 CDR"],
        when_to_buy=(
            "En luchadores con múltiples habilidades de corto cooldown que amplifican básicos. "
            "Meta para Tryndamere, Jax, Irelia, Camille. "
            "Cuando quieres daño sostenido en split push."
        ),
        synergies=["jax", "irelia", "camille", "tryndamere", "fiora"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="stridebreaker",
        name="Stridebreaker",
        cost=3300,
        description=(
            "Mítico con dash activo para luchadores que necesitan movilidad. "
            "El activo ralentiza al enemigo al entrar — anti-kite."
        ),
        stats=["50 AD", "400 HP", "20% AS", "20 CDR"],
        when_to_buy=(
            "Contra campeones muy móviles que tienes problemas de alcanzar. "
            "En luchadores que necesitan gap close propio."
        ),
        synergies=["tryndamere", "garen", "darius"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="sundered_sky",
        name="Sundered Sky",
        cost=3300,
        description=(
            "Mítico de daño single-target para luchadores con R de burst. "
            "El próximo básico después de una habilidad hace daño verdadero escalado con HP max."
        ),
        stats=["45 AD", "400 HP", "20 CDR"],
        when_to_buy=(
            "En luchadores con combo single-target. "
            "Cuando necesitas daño instantáneo sobre daño sostenido."
        ),
        synergies=["fiora", "renekton", "pantheon"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="heartsteel",
        name="Heartsteel",
        cost=2800,
        description=(
            "Mítico de HP para tanks y engagers que escalan con vida. "
            "Pasiva: gana HP permanente al atacar un epic monster o champion."
        ),
        stats=["800 HP", "20 CDR", "30 Armor", "30 MR"],
        when_to_buy=(
            "En tanks puros o campeones que escalan con HP máximo. "
            "Cuando quieres ser extremadamente difícil de matar."
        ),
        synergies=["cho_gath", "malphite", "ornn", "nasus"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="ravenous_hydra",
        name="Ravenous Hydra",
        cost=3300,
        description=(
            "Daño AoE en básicos y sustain mediante Omnivamp. "
            "Excelente para clear de oleada y duelos sostenidos."
        ),
        stats=["65 AD", "150 HP", "20 CDR"],
        when_to_buy=(
            "En luchadores que necesitan clear de oleada rápido y sustain. "
            "Combina bien con campeones con básicos que se benefician del AoE."
        ),
        synergies=["tryndamere", "fiora", "jax", "nasus"],
        patch_version="14.12",
    ),

    # ── Legendarios ───────────────────────────────────────────────────────────
    ItemDefinition(
        id="steraks_gage",
        name="Sterak's Gage",
        cost=3100,
        description=(
            "Escudo que escala con HP máximo al bajar de vida. "
            "Da AD temporal durante el escudo. "
            "Ítem de supervivencia para carries que se meten en pelea."
        ),
        stats=["50 AD", "400 HP"],
        when_to_buy=(
            "En luchadores que quieren sobrevivir bursts cuando se meten en peleas. "
            "Excelente en split pushers que pueden ser bursted 1v2."
        ),
        synergies=["tryndamere", "darius", "garen", "renekton"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="deaths_dance",
        name="Death's Dance",
        cost=3300,
        description=(
            "Convierte parte del daño recibido en un DoT (bleed). "
            "Mata un enemigo para limpiar el bleed. "
            "Sanación al eliminar un campeón."
        ),
        stats=["55 AD", "45 Armor", "15 CDR"],
        when_to_buy=(
            "Contra daño físico — la mitad del daño se bleed. "
            "En campeones que matan rápido y limpian el bleed con kills."
        ),
        countered_by=["grievous_wounds"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="wit_s_end",
        name="Wit's End",
        cost=3100,
        description=(
            "Resistencia mágica + daño mágico en básicos + velocidad de ataque. "
            "Counter principal de composiciones AP en luchadores de básicos."
        ),
        stats=["55% AS", "50 MR", "25 AD"],
        when_to_buy=(
            "Contra composiciones con mucho daño mágico. "
            "En campeones que atacan rápido y pueden usar el daño mágico extra."
        ),
        synergies=["tryndamere", "jax", "nasus"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="spirit_visage",
        name="Spirit Visage",
        cost=2900,
        description=(
            "MR + HP + amplifica toda la sanación recibida en un 25%. "
            "Fundamental para luchadores con auto-sanación."
        ),
        stats=["60 MR", "450 HP", "10 CDR"],
        when_to_buy=(
            "En luchadores con sanación propia (Tryndamere, Darius, Nasus). "
            "Contra composiciones con mucho daño mágico."
        ),
        synergies=["tryndamere", "darius", "nasus", "vladimir"],
        countered_by=["grievous_wounds"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="thornmail",
        name="Thornmail",
        cost=2700,
        description=(
            "Armor + devuelve daño físico a atacantes. "
            "Aplica Heridas Graves (Grievous Wounds) automáticamente al ser atacado."
        ),
        stats=["80 Armor", "350 HP"],
        when_to_buy=(
            "Contra campeones con mucha sanación (Master Yi, Fiora, Tryndamere). "
            "En tanks que quieren ser molestos para atacar."
        ),
        synergies=["malphite", "rammus", "ornn"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="plated_steelcaps",
        name="Plated Steelcaps",
        cost=1100,
        description=(
            "Botas de armor. Reducen el daño de básicos de campeones en un 12%. "
            "La opción de botas más frecuente en top lane."
        ),
        stats=["20 Armor", "45 MS"],
        when_to_buy=(
            "Contra composiciones mayoritariamente AD. "
            "Contra ADC o luchadores con básicos fuertes."
        ),
        patch_version="14.12",
    ),
    ItemDefinition(
        id="mercury_treads",
        name="Mercury's Treads",
        cost=1100,
        description=(
            "Botas de MR. Reducen la duración de todo CC en un 30%. "
            "Esenciales contra composiciones con mucho CC o daño mágico."
        ),
        stats=["25 MR", "45 MS"],
        when_to_buy=(
            "Contra composiciones con mucho CC o daño mágico. "
            "Cuando el mid laner enemigo es el mayor peligro."
        ),
        patch_version="14.12",
    ),
    ItemDefinition(
        id="sunfire_aegis",
        name="Sunfire Aegis",
        cost=3200,
        description=(
            "Ítem de tank que aplica quemadura AoE pasiva alrededor del portador. "
            "La quemadura escala con el tiempo en combate."
        ),
        stats=["500 HP", "35 Armor", "35 MR", "20 CDR"],
        when_to_buy=(
            "En tanks que quieren daño AoE en peleas o en el split. "
            "Contra composiciones con muchos campeones agrupados."
        ),
        synergies=["malphite", "ornn", "cho_gath"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="warmogs_armor",
        name="Warmog's Armor",
        cost=3000,
        description=(
            "Mucha HP + regeneración pasiva de HP fuera de combate. "
            "Campeones con 3000+ HP max activan la regen completa."
        ),
        stats=["800 HP", "20 CDR"],
        when_to_buy=(
            "En campeones que escalan con HP máximo (Nasus, Cho'Gath). "
            "Cuando quieres regenerar entre peleas para mantenerte en el mapa."
        ),
        synergies=["nasus", "cho_gath", "volibear"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="black_cleaver",
        name="Black Cleaver",
        cost=3000,
        description=(
            "AD + HP + reducción de armor acumulable en básicos. CDR. "
            "Counter de tanks por penetración de armor acumulada."
        ),
        stats=["40 AD", "400 HP", "20 CDR"],
        when_to_buy=(
            "Contra composiciones con mucho armor. "
            "En luchadores que atacan múltiples veces para apilar la reducción."
        ),
        synergies=["tryndamere", "darius", "garen"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="phantom_dancer",
        name="Phantom Dancer",
        cost=2600,
        description=(
            "Velocidad de ataque + probabilidad de crítico + escudo al bajar de vida. "
            "El escudo es la segunda vida del carry de crit."
        ),
        stats=["45% AS", "20% Crit", "7% MS"],
        when_to_buy=(
            "En campeones con crítico que necesitan el escudo para sobrevivir. "
            "Como ítem de supervivencia + daño en luchadores con crit (Tryndamere)."
        ),
        synergies=["tryndamere", "yasuo", "yone"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="infinity_edge",
        name="Infinity Edge",
        cost=3400,
        description=(
            "Amplifica el daño de golpes críticos. "
            "Solo eficiente con 60%+ de probabilidad de crítico."
        ),
        stats=["70 AD", "20% Crit"],
        when_to_buy=(
            "Cuando ya tienes 60%+ de probabilidad de crítico. "
            "Como ítem de hyperdamage late en carries de crit."
        ),
        synergies=["tryndamere", "jinx", "caitlyn", "yasuo"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="mortal_reminder",
        name="Mortal Reminder",
        cost=2500,
        description=(
            "AD + Heridas Graves en básicos. Counter de sanación. "
            "El ítem más importante cuando el enemigo tiene healing masivo."
        ),
        stats=["20 AD", "20% Crit", "7% MS"],
        when_to_buy=(
            "Contra composiciones con mucha sanación (Tryndamere, Fiora, Soraka). "
            "Obligatorio cuando el enemigo tiene healing significativo."
        ),
        patch_version="14.12",
    ),
    ItemDefinition(
        id="kraken_slayer",
        name="Kraken Slayer",
        cost=3400,
        description=(
            "Cada tercer básico hace daño verdadero adicional escalado con HP enemigo. "
            "Counter de tanks con mucho HP."
        ),
        stats=["45 AD", "35% AS", "20% Crit"],
        when_to_buy=(
            "Contra composiciones con mucho HP y armor (tanks). "
            "En ADC o carries de básicos contra frontlines pesadas."
        ),
        synergies=["vayne", "caitlyn", "tryndamere"],
        patch_version="14.12",
    ),
    ItemDefinition(
        id="guardian_angel",
        name="Guardian Angel",
        cost=3200,
        description=(
            "Armor + pasiva de revivir una vez cada 5 minutos al morir. "
            "Al activarse, el portador resucita con HP reducido."
        ),
        stats=["40 AD", "40 Armor"],
        when_to_buy=(
            "Cuando eres el carry principal y morir es el game over. "
            "Late game cuando un kill sobre ti cierra la partida."
        ),
        synergies=["tryndamere", "jinx", "yasuo"],
        patch_version="14.12",
    ),
]

ITEMS_BY_ID: dict[str, ItemDefinition] = {i.id: i for i in ITEMS}
