"""
backend/draft/champion_profiles.py — Perfiles de atributos por campeón.

Escala unificada 0-5 para todos los atributos.
Para añadir un campeón nuevo: agregar una entrada a CHAMPIONS.
No se necesita modificar ningún motor de scoring.

Atributos
---------
damage_type     : "physical" | "magic" | "mixed"
range           : 0 = melee · 5 = largo alcance extremo
burst           : daño instantáneo / en ventana corta
sustained_damage: DPS sostenido durante el teamfight
cc              : crowd control total
engage          : capacidad de iniciar / entrar
peel            : protección a aliados
mobility        : dashes, blinks, escapes
tankiness       : aguante base (vida, resistencias, escudos pasivos)
self_peel       : herramientas de auto-protección (invulnerabilidades, etc.)
scaling         : potencial de fin de juego / late game
anti_tank       : daño efectivo contra tanques (% vida, penetración, daño verdadero)
dive            : capacidad de alcanzar al carry enemigo
waveclear       : limpieza de oleadas de minions
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChampionProfile:
    name:             str
    damage_type:      str   # "physical" | "magic" | "mixed"
    range:            int   # 0-5
    burst:            int   # 0-5
    sustained_damage: int   # 0-5
    cc:               int   # 0-5
    engage:           int   # 0-5
    peel:             int   # 0-5
    mobility:         int   # 0-5
    tankiness:        int   # 0-5
    self_peel:        int   # 0-5
    scaling:          int   # 0-5
    anti_tank:        int   # 0-5
    dive:             int   # 0-5
    waveclear:        int   # 0-5


# ── Catálogo ──────────────────────────────────────────────────────────────────
# Ampliable añadiendo entradas. NO modificar los motores para agregar campeones.

_RAW: list[dict] = [
    # ── ADC ───────────────────────────────────────────────────────────────────
    dict(name="Jinx",         damage_type="physical", range=4, burst=2, sustained_damage=5, cc=1, engage=0, peel=0, mobility=1, tankiness=0, self_peel=1, scaling=5, anti_tank=1, dive=0, waveclear=3),
    dict(name="Caitlyn",      damage_type="physical", range=5, burst=3, sustained_damage=4, cc=2, engage=0, peel=1, mobility=2, tankiness=0, self_peel=2, scaling=3, anti_tank=1, dive=0, waveclear=3),
    dict(name="Kai'Sa",       damage_type="mixed",    range=3, burst=4, sustained_damage=4, cc=0, engage=0, peel=0, mobility=4, tankiness=0, self_peel=3, scaling=5, anti_tank=2, dive=3, waveclear=2),
    dict(name="Jhin",         damage_type="physical", range=5, burst=5, sustained_damage=2, cc=3, engage=2, peel=1, mobility=1, tankiness=0, self_peel=1, scaling=3, anti_tank=1, dive=0, waveclear=2),
    dict(name="Ezreal",       damage_type="mixed",    range=4, burst=3, sustained_damage=3, cc=0, engage=0, peel=0, mobility=4, tankiness=0, self_peel=3, scaling=3, anti_tank=1, dive=1, waveclear=2),
    dict(name="Miss Fortune",  damage_type="physical", range=3, burst=5, sustained_damage=3, cc=2, engage=3, peel=0, mobility=1, tankiness=0, self_peel=1, scaling=3, anti_tank=1, dive=0, waveclear=3),
    dict(name="Vayne",        damage_type="physical", range=2, burst=3, sustained_damage=4, cc=1, engage=0, peel=0, mobility=3, tankiness=0, self_peel=2, scaling=5, anti_tank=5, dive=2, waveclear=1),
    dict(name="Ashe",         damage_type="physical", range=4, burst=2, sustained_damage=4, cc=4, engage=3, peel=1, mobility=0, tankiness=1, self_peel=1, scaling=3, anti_tank=1, dive=0, waveclear=3),
    dict(name="Samira",       damage_type="physical", range=2, burst=5, sustained_damage=4, cc=2, engage=3, peel=0, mobility=3, tankiness=0, self_peel=2, scaling=4, anti_tank=1, dive=4, waveclear=2),
    dict(name="Twitch",       damage_type="physical", range=4, burst=4, sustained_damage=4, cc=1, engage=0, peel=0, mobility=1, tankiness=0, self_peel=1, scaling=5, anti_tank=2, dive=1, waveclear=3),
    dict(name="Zeri",         damage_type="physical", range=3, burst=3, sustained_damage=4, cc=1, engage=1, peel=0, mobility=5, tankiness=0, self_peel=3, scaling=4, anti_tank=1, dive=2, waveclear=2),
    dict(name="Draven",       damage_type="physical", range=3, burst=4, sustained_damage=5, cc=2, engage=1, peel=0, mobility=1, tankiness=0, self_peel=1, scaling=2, anti_tank=1, dive=0, waveclear=2),
    dict(name="Lucian",       damage_type="physical", range=3, burst=4, sustained_damage=3, cc=1, engage=1, peel=1, mobility=3, tankiness=0, self_peel=2, scaling=2, anti_tank=1, dive=1, waveclear=3),
    dict(name="Xayah",        damage_type="physical", range=4, burst=3, sustained_damage=4, cc=2, engage=0, peel=2, mobility=2, tankiness=0, self_peel=4, scaling=4, anti_tank=1, dive=0, waveclear=3),
    dict(name="Kog'Maw",      damage_type="mixed",    range=5, burst=2, sustained_damage=5, cc=1, engage=0, peel=0, mobility=0, tankiness=0, self_peel=0, scaling=5, anti_tank=3, dive=0, waveclear=3),
    dict(name="Aphelios",     damage_type="physical", range=4, burst=4, sustained_damage=4, cc=2, engage=2, peel=0, mobility=1, tankiness=0, self_peel=0, scaling=5, anti_tank=2, dive=0, waveclear=3),
    dict(name="Sivir",        damage_type="physical", range=3, burst=2, sustained_damage=3, cc=1, engage=2, peel=2, mobility=2, tankiness=0, self_peel=3, scaling=3, anti_tank=1, dive=0, waveclear=5),
    dict(name="Varus",        damage_type="mixed",    range=4, burst=4, sustained_damage=3, cc=4, engage=3, peel=0, mobility=1, tankiness=0, self_peel=1, scaling=3, anti_tank=2, dive=0, waveclear=3),
    dict(name="Tristana",     damage_type="physical", range=4, burst=5, sustained_damage=3, cc=2, engage=0, peel=0, mobility=3, tankiness=0, self_peel=2, scaling=4, anti_tank=1, dive=3, waveclear=3),
    dict(name="Kalista",      damage_type="physical", range=3, burst=2, sustained_damage=4, cc=2, engage=1, peel=3, mobility=5, tankiness=0, self_peel=2, scaling=4, anti_tank=1, dive=1, waveclear=3),
    dict(name="Nilah",        damage_type="physical", range=1, burst=4, sustained_damage=4, cc=2, engage=3, peel=0, mobility=3, tankiness=1, self_peel=3, scaling=4, anti_tank=1, dive=3, waveclear=2),
    dict(name="Corki",        damage_type="mixed",    range=4, burst=4, sustained_damage=3, cc=1, engage=1, peel=0, mobility=3, tankiness=0, self_peel=2, scaling=3, anti_tank=2, dive=0, waveclear=3),

    # ── TOP ───────────────────────────────────────────────────────────────────
    dict(name="Darius",       damage_type="physical", range=1, burst=4, sustained_damage=4, cc=3, engage=2, peel=0, mobility=1, tankiness=4, self_peel=1, scaling=4, anti_tank=2, dive=2, waveclear=3),
    dict(name="Garen",        damage_type="physical", range=1, burst=4, sustained_damage=3, cc=2, engage=1, peel=0, mobility=2, tankiness=4, self_peel=3, scaling=3, anti_tank=1, dive=2, waveclear=3),
    dict(name="Fiora",        damage_type="physical", range=1, burst=3, sustained_damage=4, cc=2, engage=1, peel=0, mobility=3, tankiness=2, self_peel=4, scaling=5, anti_tank=5, dive=3, waveclear=2),
    dict(name="Irelia",       damage_type="physical", range=1, burst=4, sustained_damage=4, cc=3, engage=3, peel=0, mobility=4, tankiness=2, self_peel=2, scaling=4, anti_tank=2, dive=4, waveclear=3),
    dict(name="Camille",      damage_type="physical", range=1, burst=4, sustained_damage=3, cc=4, engage=4, peel=1, mobility=4, tankiness=1, self_peel=2, scaling=4, anti_tank=2, dive=5, waveclear=2),
    dict(name="Jax",          damage_type="mixed",    range=1, burst=3, sustained_damage=4, cc=2, engage=2, peel=0, mobility=3, tankiness=3, self_peel=3, scaling=5, anti_tank=1, dive=3, waveclear=2),
    dict(name="Malphite",     damage_type="magic",    range=2, burst=3, sustained_damage=2, cc=5, engage=5, peel=2, mobility=2, tankiness=5, self_peel=2, scaling=2, anti_tank=1, dive=3, waveclear=2),
    dict(name="Ornn",         damage_type="magic",    range=1, burst=3, sustained_damage=3, cc=5, engage=4, peel=2, mobility=1, tankiness=5, self_peel=2, scaling=4, anti_tank=1, dive=2, waveclear=3),
    dict(name="Aatrox",       damage_type="physical", range=1, burst=3, sustained_damage=4, cc=3, engage=3, peel=0, mobility=2, tankiness=3, self_peel=3, scaling=4, anti_tank=1, dive=3, waveclear=3),
    dict(name="Riven",        damage_type="physical", range=1, burst=5, sustained_damage=3, cc=3, engage=4, peel=0, mobility=4, tankiness=2, self_peel=2, scaling=4, anti_tank=1, dive=4, waveclear=3),
    dict(name="Renekton",     damage_type="physical", range=1, burst=5, sustained_damage=3, cc=3, engage=3, peel=0, mobility=3, tankiness=3, self_peel=2, scaling=2, anti_tank=1, dive=3, waveclear=3),
    dict(name="Nasus",        damage_type="physical", range=1, burst=3, sustained_damage=3, cc=2, engage=1, peel=0, mobility=1, tankiness=4, self_peel=2, scaling=5, anti_tank=1, dive=1, waveclear=4),
    dict(name="Gwen",         damage_type="magic",    range=1, burst=3, sustained_damage=4, cc=2, engage=1, peel=0, mobility=2, tankiness=2, self_peel=4, scaling=5, anti_tank=3, dive=2, waveclear=3),
    dict(name="Jayce",        damage_type="physical", range=3, burst=5, sustained_damage=3, cc=2, engage=2, peel=0, mobility=2, tankiness=1, self_peel=1, scaling=3, anti_tank=1, dive=1, waveclear=4),
    dict(name="Kennen",       damage_type="magic",    range=3, burst=4, sustained_damage=3, cc=4, engage=4, peel=0, mobility=3, tankiness=1, self_peel=2, scaling=3, anti_tank=1, dive=3, waveclear=3),
    dict(name="Shen",         damage_type="physical", range=1, burst=2, sustained_damage=3, cc=3, engage=3, peel=5, mobility=1, tankiness=5, self_peel=2, scaling=3, anti_tank=1, dive=2, waveclear=2),
    dict(name="Maokai",       damage_type="magic",    range=1, burst=2, sustained_damage=2, cc=4, engage=3, peel=2, mobility=1, tankiness=5, self_peel=1, scaling=2, anti_tank=1, dive=2, waveclear=3),
    dict(name="Tryndamere",   damage_type="physical", range=1, burst=4, sustained_damage=4, cc=1, engage=1, peel=0, mobility=2, tankiness=2, self_peel=5, scaling=5, anti_tank=1, dive=4, waveclear=3),
    dict(name="K'Sante",      damage_type="mixed",    range=1, burst=3, sustained_damage=3, cc=4, engage=4, peel=2, mobility=3, tankiness=5, self_peel=3, scaling=3, anti_tank=1, dive=3, waveclear=2),
    dict(name="Teemo",        damage_type="magic",    range=3, burst=4, sustained_damage=3, cc=2, engage=0, peel=0, mobility=2, tankiness=0, self_peel=2, scaling=3, anti_tank=1, dive=1, waveclear=3),
    dict(name="Urgot",        damage_type="physical", range=2, burst=4, sustained_damage=4, cc=3, engage=2, peel=0, mobility=2, tankiness=3, self_peel=2, scaling=3, anti_tank=3, dive=2, waveclear=3),
    dict(name="Cho'Gath",     damage_type="magic",    range=1, burst=4, sustained_damage=2, cc=4, engage=2, peel=1, mobility=1, tankiness=5, self_peel=2, scaling=4, anti_tank=3, dive=2, waveclear=3),
    dict(name="Mordekaiser",  damage_type="magic",    range=1, burst=3, sustained_damage=4, cc=3, engage=2, peel=0, mobility=1, tankiness=4, self_peel=3, scaling=5, anti_tank=3, dive=2, waveclear=3),
    dict(name="Illaoi",       damage_type="physical", range=1, burst=4, sustained_damage=4, cc=2, engage=1, peel=0, mobility=1, tankiness=3, self_peel=2, scaling=4, anti_tank=1, dive=1, waveclear=3),
    dict(name="Poppy",        damage_type="physical", range=1, burst=3, sustained_damage=3, cc=4, engage=3, peel=4, mobility=2, tankiness=4, self_peel=2, scaling=2, anti_tank=1, dive=2, waveclear=2),
]

# Construir el dict de búsqueda por nombre (case-insensitive)
CHAMPIONS: dict[str, ChampionProfile] = {
    d["name"].lower(): ChampionProfile(**d) for d in _RAW
}


def get_profile(name: str) -> ChampionProfile | None:
    """
    Retorna el perfil del campeón o None si no está en el catálogo.
    La búsqueda es case-insensitive.
    """
    return CHAMPIONS.get(name.lower())


def all_profiles() -> list[ChampionProfile]:
    """Lista de todos los perfiles registrados."""
    return list(CHAMPIONS.values())
