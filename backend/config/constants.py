"""
backend/config/constants.py — Constantes compartidas entre módulos.

Solo contiene valores usados en más de un módulo.
Las constantes específicas de cada módulo viven junto a su código.
"""

# Umbrales de muestra
MIN_GAMES_TABLE    = 2    # mínimo para aparecer en tablas de campeón
MIN_GAMES_QUALIFY  = 3    # mínimo para clasificación y grade
MIN_GAMES_RELIABLE = 10   # mínimo para análisis confiable
MIN_GAMES_ROBUST   = 20   # mínimo para análisis robusto

# Confianza estadística: con esta cantidad de partidas se considera muestra completa
CONFIDENCE_FULL_GAMES = 10

# Clasificación de traps: WR ≤ este umbral → pick trampa
TRAP_WR_MAX = 0.40

# Dependencia de pool: si el campeón principal supera este % → advertencia
DEPENDENCY_HIGH = 0.50

# Matchup Intelligence
MIN_MATCHUP_GAMES    = 3   # mínimo de partidas contra un campeón para mostrar matchup
ROBUST_MATCHUP_GAMES = 8   # muestra considerada robusta (badge confiable)

# Champion Coach
MIN_CHAMPION_GAMES    = 5   # mínimo para análisis completo de un campeón
ROBUST_CHAMPION_GAMES = 10  # muestra robusta para coach de campeón
