"""
Ruta de aprendizaje oficial para Tryndamere TOP.

ROADMAP es importado por el perfil y por LearningIntelligenceEngine.
ID: "tryndamere_top_v1"
"""

from backend.game_intelligence.models.learning import (
    LearningRoadmap, LearningLevel, GraduationCriteria,
)

ROADMAP = LearningRoadmap(
    id="tryndamere_top_v1",
    champion="tryndamere",
    role="TOP",
    notes=(
        "Tryndamere es un campeón de late game escalado. "
        "El aprendizaje progresa desde sobrevivir la fase de carriles "
        "hasta dominar el split push y el uso táctico de la R."
    ),
    total_estimated_games=120,
    patch_version="14.12",
    levels=[

        LearningLevel(
            level=1,
            name="Supervivencia en Lane",
            description=(
                "El objetivo en este nivel es llegar a late game sin perder "
                "demasiado terreno. Tryndamere es débil en early — sobrevivir "
                "es más importante que ganar el carril."
            ),
            focus_areas=[
                "Morir menos de 4 veces por partida.",
                "No sobreextenderse sin visión del río.",
                "Usar Q para recuperar vida cuando baja del 50%.",
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
                GraduationCriteria(
                    id="lvl1_cs",
                    description="Conseguir más de 5.0 CS/min en 4 de 5 partidas",
                    evaluation_mode="auto",
                    metric_key="cs_per_min",
                    threshold=5.0,
                    window_games=5,
                    required_successes=4,
                ),
            ],
            drill_ids=["wave_crash_timing", "deaths_lt_threshold"],
            estimated_games=15,
        ),

        LearningLevel(
            level=2,
            name="Gestión de Oleada Básica",
            description=(
                "Aprender a gestionar la oleada para crear ventanas de recall seguro "
                "y reducir la presión de ganks. Crashear antes de recall."
            ),
            focus_areas=[
                "Crashear la oleada antes de cada recall.",
                "Usar Freeze cuando el enemigo está bajo de vida o en recall.",
                "Wardear el río antes de pushear.",
            ],
            prerequisite_level=1,
            graduation_criteria=[
                GraduationCriteria(
                    id="lvl2_cs_improved",
                    description="Más de 6.0 CS/min en 4 de 5 partidas",
                    evaluation_mode="auto",
                    metric_key="cs_per_min",
                    threshold=6.0,
                    window_games=5,
                    required_successes=4,
                ),
                GraduationCriteria(
                    id="lvl2_deaths",
                    description="Morir menos de 3 veces en 4 de 5 partidas",
                    evaluation_mode="auto",
                    metric_key="deaths",
                    threshold=3.0,
                    window_games=5,
                    required_successes=4,
                ),
            ],
            drill_ids=["wave_freeze_fundamentals", "wave_crash_timing", "macro_recall_timing"],
            estimated_games=20,
        ),

        LearningLevel(
            level=3,
            name="Power Spike Awareness (R)",
            description=(
                "Aprender a usar correctamente la R de Tryndamere. "
                "La R no es para iniciar peleas — es para sobrevivir y curar con Q. "
                "Activar con suficiente furia para la Q."
            ),
            focus_areas=[
                "Activar R cuando estás a 15-20% de vida, no más tarde.",
                "Tener alta furia antes de entrar en una pelea.",
                "No malgastar R en situaciones donde no es necesaria.",
            ],
            prerequisite_level=2,
            graduation_criteria=[
                GraduationCriteria(
                    id="lvl3_winrate",
                    description="Alcanzar 45%+ de winrate en Tryndamere en últimas 20 partidas",
                    evaluation_mode="semi_auto",
                    metric_key="win",
                    threshold=0.45,
                    window_games=20,
                    required_successes=9,
                ),
                GraduationCriteria(
                    id="lvl3_kda",
                    description="KDA >= 2.0 en 4 de 5 partidas",
                    evaluation_mode="auto",
                    metric_key="kda",
                    threshold=2.0,
                    window_games=5,
                    required_successes=4,
                ),
            ],
            drill_ids=["r_activation_timing", "fury_management"],
            estimated_games=25,
        ),

        LearningLevel(
            level=4,
            name="Split Push Básico",
            description=(
                "Empezar a usar el split push como win condition primaria. "
                "Tryndamere gana partidas tomando estructuras, no matando."
            ),
            focus_areas=[
                "Ir al carril lateral después del primer ítem completado.",
                "Comunicar el split al equipo con el chat de equipo.",
                "Retirarse cuando 2+ enemigos roten — no 1v2 innecesario.",
            ],
            prerequisite_level=3,
            graduation_criteria=[
                GraduationCriteria(
                    id="lvl4_structures",
                    description="Destruir al menos 2 torres por partida en 3 de 5 partidas",
                    evaluation_mode="auto",
                    metric_key="turret_kills",
                    threshold=2.0,
                    window_games=5,
                    required_successes=3,
                ),
                GraduationCriteria(
                    id="lvl4_winrate",
                    description="Alcanzar 50%+ de winrate en últimas 20 partidas",
                    evaluation_mode="semi_auto",
                    metric_key="win",
                    threshold=0.50,
                    window_games=20,
                    required_successes=10,
                ),
            ],
            drill_ids=["macro_split_push_execution", "macro_recall_timing"],
            estimated_games=25,
        ),

        LearningLevel(
            level=5,
            name="Split Push Avanzado y Macro",
            description=(
                "Dominar el split push avanzado: leer las rotaciones enemigas, "
                "coordinar con el equipo para crear el dilema correcto, "
                "y tomar decisiones de cuándo pelear vs cuándo retirarse."
            ),
            focus_areas=[
                "Leer cuándo el equipo enemigo puede contestar el split.",
                "Convertir la presión del split en objetivos o el Nexus.",
                "Sincronizar el TP con las peleas del equipo.",
            ],
            prerequisite_level=4,
            graduation_criteria=[
                GraduationCriteria(
                    id="lvl5_winrate",
                    description="Alcanzar 55%+ de winrate en últimas 30 partidas",
                    evaluation_mode="semi_auto",
                    metric_key="win",
                    threshold=0.55,
                    window_games=30,
                    required_successes=17,
                ),
            ],
            drill_ids=["macro_split_push_execution", "macro_rotation_with_crash"],
            estimated_games=35,
        ),
    ],
)
