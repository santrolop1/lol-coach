"""
backend/draft/profile_builder.py — Construcción de TeamProfile y EnemyProfile.

Convierte listas de nombres de campeones en perfiles de atributos agregados.
Si un campeón no está en el catálogo se omite silenciosamente.
"""

from __future__ import annotations

from .champion_profiles import get_profile
from .draft_context import TeamProfile, EnemyProfile


def build_team_profile(champion_names: list[str]) -> TeamProfile:
    """
    Construye el TeamProfile a partir de los nombres de campeones aliados.

    Parámetros
    ----------
    champion_names : lista de nombres tal como vienen del LCU (pueden tener
                     mayúsculas variables, apostrofes, etc.)

    Retorna
    -------
    TeamProfile con atributos sumados de todos los perfiles encontrados.
    El campo `count` refleja cuántos campeones tenían perfil registrado.
    """
    profile = TeamProfile()

    for name in champion_names:
        p = get_profile(name)
        if p is None:
            continue

        profile.count += 1
        profile.total_burst            += p.burst
        profile.total_sustained        += p.sustained_damage
        profile.total_cc               += p.cc
        profile.total_engage           += p.engage
        profile.total_peel             += p.peel
        profile.total_mobility         += p.mobility
        profile.total_tankiness        += p.tankiness
        profile.total_self_peel        += p.self_peel
        profile.total_scaling          += p.scaling
        profile.total_anti_tank        += p.anti_tank
        profile.total_dive             += p.dive
        profile.total_waveclear        += p.waveclear

        if p.damage_type == "magic":
            profile.magic_count += 1
        elif p.damage_type == "mixed":
            profile.mixed_count += 1
        else:
            profile.physical_count += 1

    return profile


def build_enemy_profile(champion_names: list[str]) -> EnemyProfile:
    """
    Construye el EnemyProfile a partir de los nombres de campeones enemigos.

    Los flags de amenaza (high_burst, high_dive, etc.) se calculan
    automáticamente como propiedades derivadas del promedio.
    """
    profile = EnemyProfile()

    for name in champion_names:
        p = get_profile(name)
        if p is None:
            continue

        profile.count        += 1
        profile.total_burst  += p.burst
        profile.total_dive   += p.dive
        profile.total_cc     += p.cc
        profile.total_engage += p.engage
        profile.total_anti_tank += p.anti_tank
        profile.total_scaling   += p.scaling
        profile.total_mobility  += p.mobility
        profile.total_peel      += p.peel

    return profile
