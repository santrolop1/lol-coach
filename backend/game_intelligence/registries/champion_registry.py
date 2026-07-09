"""
ChampionRegistry — auto-descubrimiento de perfiles de campeón.

Convención:
  knowledge/champions/{slug}/profile.py  →  PROFILE: ChampionProfile
  knowledge/champions/{slug}/matchups/{enemy}.py  →  MATCHUP: MatchupProfile

Agregar un campeón nuevo = crear un directorio. Cero cambios al registry.
"""

from __future__ import annotations
import importlib
import logging
from pathlib import Path
from typing import Any

from .base import BaseRegistry
from ..models.champion import ChampionProfile
from ..models.matchup import MatchupProfile

logger = logging.getLogger(__name__)

_KNOWLEDGE_ROOT = Path(__file__).parent.parent / "knowledge" / "champions"


class ChampionRegistry(BaseRegistry):

    # ── Perfiles de campeón ───────────────────────────────────────────────────

    def get(self, key: str, *args: Any) -> ChampionProfile | None:
        """
        Carga el ChampionProfile de un campeón.
        key = slug del campeón (ej: "tryndamere").
        args[0] = role opcional (no usado en la carga — el profile incluye todos los roles).
        """
        slug = key.lower()
        cache_k = self._cache_key("profile", slug)
        if cache_k in self._cache:
            return self._cache[cache_k]

        module_path = f"backend.game_intelligence.knowledge.champions.{slug}.profile"
        try:
            mod = importlib.import_module(module_path)
            profile: ChampionProfile = mod.PROFILE
            self._cache[cache_k] = profile
            return profile
        except ModuleNotFoundError:
            return None
        except AttributeError:
            logger.warning("profile.py de '%s' no exporta PROFILE", slug)
            return None
        except Exception as exc:
            logger.error("Error cargando perfil '%s': %s", slug, exc)
            return None

    def exists(self, key: str, *args: Any) -> bool:
        slug = key.lower()
        return (_KNOWLEDGE_ROOT / slug / "profile.py").exists()

    def list_available(self) -> list[str]:
        if not _KNOWLEDGE_ROOT.exists():
            return []
        return sorted(
            d.name for d in _KNOWLEDGE_ROOT.iterdir()
            if d.is_dir() and (d / "profile.py").exists()
        )

    def validate(self, item: Any) -> list[str]:
        errors: list[str] = []
        if not isinstance(item, ChampionProfile):
            return ["item no es ChampionProfile"]
        if not item.champion:
            errors.append("champion está vacío")
        if not item.display_name:
            errors.append("display_name está vacío")
        if not item.roles:
            errors.append("roles está vacío")
        if not item.patch_version:
            errors.append("patch_version está vacío")
        if not item.identity:
            errors.append("identity está vacío")
        return errors

    # ── Matchups ──────────────────────────────────────────────────────────────

    def get_matchup(self, champion: str, enemy: str, role: str) -> MatchupProfile | None:
        """Carga el MatchupProfile de champion vs enemy en el role dado."""
        champ_slug = champion.lower()
        enemy_slug = enemy.lower()
        cache_k = self._cache_key("matchup", champ_slug, enemy_slug, role.lower())
        if cache_k in self._cache:
            return self._cache[cache_k]

        module_path = (
            f"backend.game_intelligence.knowledge.champions"
            f".{champ_slug}.matchups.{enemy_slug}"
        )
        try:
            mod = importlib.import_module(module_path)
            matchup: MatchupProfile = mod.MATCHUP
            self._cache[cache_k] = matchup
            return matchup
        except ModuleNotFoundError:
            return None
        except AttributeError:
            logger.warning("matchup %s vs %s no exporta MATCHUP", champ_slug, enemy_slug)
            return None
        except Exception as exc:
            logger.error("Error cargando matchup %s vs %s: %s", champ_slug, enemy_slug, exc)
            return None

    def matchup_exists(self, champion: str, enemy: str) -> bool:
        slug = champion.lower()
        enemy_slug = enemy.lower()
        return (_KNOWLEDGE_ROOT / slug / "matchups" / f"{enemy_slug}.py").exists()

    def list_matchups(self, champion: str) -> list[str]:
        """Devuelve lista de enemigos con MatchupProfile disponible."""
        matchups_dir = _KNOWLEDGE_ROOT / champion.lower() / "matchups"
        if not matchups_dir.exists():
            return []
        return sorted(
            f.stem for f in matchups_dir.glob("*.py")
            if f.name != "__init__.py"
        )

    def list_roles(self, champion: str) -> list[str]:
        profile = self.get(champion)
        if profile is None:
            return []
        return profile.roles

    def coverage_report(self) -> dict[str, list[str]]:
        """Devuelve {champion: [enemies_with_matchup]} para todos los campeones."""
        return {
            champ: self.list_matchups(champ)
            for champ in self.list_available()
        }
