"""
Perfiles de campeón.

Convención de auto-descubrimiento por ChampionRegistry:
  {champion_slug}/
    profile.py      →  PROFILE: ChampionProfile
    mechanics.py    →  importado por profile.py
    builds.py       →  importado por profile.py
    macro.py        →  importado por profile.py
    matchups/
      {enemy}.py    →  MATCHUP: MatchupProfile

Agregar un campeón = crear un directorio. Sin modificar ningún motor.
"""
