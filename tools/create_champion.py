"""
Generador de nuevo Champion Profile.

Uso:
    python tools/create_champion.py <nombre_campeon> [role]

Ejemplo:
    python tools/create_champion.py jinx ADC
    python tools/create_champion.py darius TOP

Genera toda la estructura de directorios y archivos plantilla
siguiendo el Gold Standard definido por Tryndamere.
"""

from __future__ import annotations
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHAMPIONS_DIR = ROOT / "backend" / "game_intelligence" / "knowledge" / "champions"


def _to_slug(name: str) -> str:
    """Convierte 'Aurelion Sol' a 'aurelion_sol'."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9 ]", "", slug)
    return slug.replace(" ", "_")


def _to_display(slug: str) -> str:
    return slug.replace("_", " ").title()


def create_champion(name: str, role: str = "TOP") -> Path:
    slug = _to_slug(name)
    display = _to_display(slug)
    champ_dir = CHAMPIONS_DIR / slug

    if champ_dir.exists():
        print(f"⚠  El campeón '{slug}' ya existe en {champ_dir}")
        return champ_dir

    # Crear directorios
    (champ_dir / "matchups").mkdir(parents=True)
    print(f"✓ Directorio creado: {champ_dir}")

    # __init__.py
    (champ_dir / "__init__.py").write_text(
        f'"""Perfil y conocimiento de {display}."""\n', encoding="utf-8"
    )
    (champ_dir / "matchups" / "__init__.py").write_text(
        f'"""Matchups de {display}."""\n', encoding="utf-8"
    )

    # profile.py
    _write_profile_template(champ_dir / "profile.py", slug, display, role)

    # learning.py
    _write_learning_template(champ_dir / "learning.py", slug, display, role)

    print(f"✓ {display} listo en: {champ_dir}")
    print(f"  Archivos generados:")
    for f in sorted(champ_dir.rglob("*.py")):
        print(f"    {f.relative_to(ROOT)}")
    print()
    print("Próximos pasos:")
    print(f"  1. Editar backend/game_intelligence/knowledge/champions/{slug}/profile.py")
    print(f"  2. Editar backend/game_intelligence/knowledge/champions/{slug}/learning.py")
    print(f"  3. Añadir matchups en matchups/{{enemy}}.py")
    print(f"  4. Validar con: python -m pytest tests/test_game_intelligence_gi3.py -k {slug}")

    return champ_dir


def _write_profile_template(path: Path, slug: str, display: str, role: str) -> None:
    content = f'''"""
{display} — Champion Profile.

Generado con create_champion.py — completar manualmente.
Referencia: knowledge/champions/tryndamere/profile.py (Gold Standard)
"""

from backend.game_intelligence.models.champion import (
    ChampionProfile, AbilityInfo,
    Combo, PowerSpike,
    ChampionMacroConfig, ChampionWaveConfig,
    ChampionBuildConfig, ChampionRuneConfig,
)
from backend.game_intelligence.models.common import KnowledgeSource, Confidence, SourceType

_SOURCE = KnowledgeSource(
    type=SourceType.COMMUNITY,
    author="",
    confidence=Confidence.MEDIUM,
    date="",
    url=None,
    notes="TODO: completar fuente.",
)

PROFILE = ChampionProfile(
    champion="{slug}",
    display_name="{display}",
    roles=["{role}"],
    difficulty="medium",         # "low" | "medium" | "high" | "extreme"
    patch_version="14.12",
    identity="TODO: Una oración — qué tipo de campeón es.",
    playstyle="scaling",         # "early_dominant" | "scaling" | "flex"
    scaling="late",              # "early" | "mid" | "late" | "all_game"

    strengths=[
        "TODO: fortaleza 1.",
        "TODO: fortaleza 2.",
    ],
    weaknesses=[
        "TODO: debilidad 1.",
        "TODO: debilidad 2.",
    ],

    abilities={{
        "P": AbilityInfo(
            key="P",
            name="TODO: Nombre de la pasiva",
            description="TODO: Descripción mecánica relevante.",
            tips=["TODO: consejo 1."],
            common_mistakes=["TODO: error 1."],
            max_rank_priority=3,
        ),
        "Q": AbilityInfo(
            key="Q",
            name="TODO: Nombre del Q",
            description="TODO: Descripción mecánica relevante.",
            tips=["TODO: consejo 1."],
            common_mistakes=["TODO: error 1."],
            cooldowns=[12.0, 11.0, 10.0, 9.0, 8.0],
            cost="TODO: coste",
            max_rank_priority=1,
        ),
        "W": AbilityInfo(
            key="W",
            name="TODO: Nombre del W",
            description="TODO: Descripción mecánica relevante.",
            tips=[],
            common_mistakes=[],
            cooldowns=[14.0, 14.0, 14.0, 14.0, 14.0],
            max_rank_priority=3,
        ),
        "E": AbilityInfo(
            key="E",
            name="TODO: Nombre del E",
            description="TODO: Descripción mecánica relevante.",
            tips=[],
            common_mistakes=[],
            cooldowns=[12.0, 11.0, 10.0, 9.0, 8.0],
            max_rank_priority=2,
        ),
        "R": AbilityInfo(
            key="R",
            name="TODO: Nombre del R",
            description="TODO: Descripción mecánica relevante.",
            tips=["TODO: consejo del R."],
            common_mistakes=["TODO: error del R."],
            cooldowns=[120.0, 100.0, 80.0],
            max_rank_priority=1,
        ),
    }},
    ability_order=["Q", "E", "W"],  # TODO: ajustar

    combos=[
        Combo(
            id="basic_trade",
            name="Intercambio básico",
            sequence=["TODO: ability 1", "AA", "TODO: ability 2"],
            description="TODO: descripción.",
            when_to_use="TODO: cuándo usarlo.",
            difficulty="basic",
        ),
    ],

    power_spikes=[
        PowerSpike(
            id="level_6",
            timing="Nivel 6",
            description="TODO: por qué el nivel 6 importa.",
            action="TODO: qué hacer al llegar a nivel 6.",
            window_minutes=(8.0, 12.0),
        ),
        PowerSpike(
            id="first_item",
            timing="Primer ítem completado",
            description="TODO: por qué el primer ítem importa.",
            action="TODO: qué hacer al completarlo.",
            window_minutes=(14.0, 20.0),
        ),
    ],

    macro_config=ChampionMacroConfig(
        primary_pattern_ids=["recall_timing"],  # TODO: añadir más
        win_condition_ids=["teamfight_and_win"],  # TODO: ajustar
        split_push_priority="conditional",  # "always"|"conditional"|"rarely"|"never"
        teamfight_role="frontline",
    ),

    wave_config=ChampionWaveConfig(
        preferred_technique_ids=["crash", "fast_push"],  # TODO: ajustar
        level_2_crash=False,
        recall_setup_technique_id="crash",
    ),

    build_config=ChampionBuildConfig(
        standard_build_id="TODO: ID del ItemBuild estándar",
        starter_id="TODO: ID del starter item",
        boots_options=["plated_steelcaps", "mercury_treads"],
    ),

    rune_config=ChampionRuneConfig(
        standard_page_id="TODO: ID de la RunePage estándar",
    ),

    common_mistakes=[
        "TODO: error más frecuente 1.",
        "TODO: error más frecuente 2.",
    ],
    tips=[
        "TODO: consejo más importante 1.",
        "TODO: consejo más importante 2.",
    ],

    learning_roadmap_id="{slug}_{role.lower()}_v1",

    sources=[_SOURCE],
    last_updated="TODO: fecha",
)
'''
    path.write_text(content, encoding="utf-8")


def _write_learning_template(path: Path, slug: str, display: str, role: str) -> None:
    content = f'''"""
Ruta de aprendizaje para {display} {role}.

Generado con create_champion.py — completar manualmente.
Referencia: knowledge/champions/tryndamere/learning.py (Gold Standard)
"""

from backend.game_intelligence.models.learning import (
    LearningRoadmap, LearningLevel, GraduationCriteria,
)

ROADMAP = LearningRoadmap(
    id="{slug}_{role.lower()}_v1",
    champion="{slug}",
    role="{role}",
    notes="TODO: descripción general de la ruta de aprendizaje.",
    total_estimated_games=80,
    patch_version="14.12",
    levels=[
        LearningLevel(
            level=1,
            name="Fundamentos",
            description="TODO: qué se aprende en este nivel.",
            focus_areas=[
                "TODO: foco 1.",
                "TODO: foco 2.",
            ],
            graduation_criteria=[
                GraduationCriteria(
                    id="lvl1_deaths",
                    description="Morir menos de 4 veces en 4 de 5 partidas",
                    evaluation_mode="auto",
                    metric_key="deaths",
                    threshold=4.0,
                    window_games=5,
                    required_successes=4,
                ),
            ],
            drill_ids=["deaths_lt_threshold"],
            estimated_games=20,
        ),
        # TODO: añadir más niveles
    ],
)
'''
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tools/create_champion.py <nombre_campeon> [role]")
        print("Ejemplo: python tools/create_champion.py jinx ADC")
        sys.exit(1)

    name = sys.argv[1]
    role = sys.argv[2].upper() if len(sys.argv) > 2 else "TOP"
    create_champion(name, role)
