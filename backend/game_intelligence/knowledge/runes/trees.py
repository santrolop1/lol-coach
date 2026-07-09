"""
Los 5 árboles de runas de League of Legends.
"""

from backend.game_intelligence.models.rune import RuneTree

TREES: list[RuneTree] = [
    RuneTree(
        id="precision",
        name="Precision",
        description="Daño y velocidad de ataque mejorados. Para carries y atacantes básicos.",
        playstyle="Combate sostenido, básicos potenciados, daño escalonado.",
    ),
    RuneTree(
        id="domination",
        name="Domination",
        description="Burst de daño y acceso a targets. Para assassins y snowballers.",
        playstyle="Daño rápido, engage, execución de targets vulnerables.",
    ),
    RuneTree(
        id="sorcery",
        name="Sorcery",
        description="Potenciación de habilidades y movimiento. Para mages y poke.",
        playstyle="Daño de habilidades, poke, utility y movilidad.",
    ),
    RuneTree(
        id="resolve",
        name="Resolve",
        description="Durabilidad y CC. Para tanks y supports defensivos.",
        playstyle="Aguantar daño, crowd control, escalar con HP.",
    ),
    RuneTree(
        id="inspiration",
        name="Inspiration",
        description="Trampas y cambios de reglas. Para patrones de juego creativos.",
        playstyle="Ítems gratis, cooldowns reducidos, modificación de reglas.",
    ),
]

TREES_BY_ID: dict[str, RuneTree] = {t.id: t for t in TREES}
