"""
GameIntelligencePlatform — Fachada principal de la plataforma.

Orquesta todos los motores de inteligencia.
Los consumidores (FastAPI routes, ViewModels) interactúan solo con esta clase.

Estado en GI-1: esqueleto con métodos vacíos.
Los motores se conectan en GI-3 a GI-8.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field

from .registries import knowledge, KnowledgeAPI
from .models.champion import ChampionProfile
from .models.matchup import MatchupProfile
from .models.learning import LearningState
from .models.training import ActiveDrill
from .models.review import EnrichedReview

logger = logging.getLogger(__name__)


@dataclass
class ChampionContext:
    """Resultado de build() — todo lo que la UI necesita sobre un campeón."""
    champion: str
    role: str
    has_profile: bool = False
    has_matchup_profile: bool = False
    profile: ChampionProfile | None = None
    matchup_profile: MatchupProfile | None = None
    learning_state: LearningState | None = None
    active_drill: ActiveDrill | None = None
    last_review: EnrichedReview | None = None
    patterns: list[dict] = field(default_factory=list)
    priorities: list[dict] = field(default_factory=list)
    confidence: str = "insufficient"
    games_on_champion: int = 0
    winrate: float | None = None
    avg_score: float | None = None


class GameIntelligencePlatform:
    """
    Plataforma de inteligencia de juego.

    Principios:
    - Nunca leer knowledge/ directamente — siempre vía self.knowledge
    - Nunca if champion == "X" — toda la lógica es genérica
    - Degradación elegante: funciona sin perfil (análisis estadístico puro)
    """

    def __init__(self, knowledge_api: KnowledgeAPI | None = None) -> None:
        self.knowledge = knowledge_api or knowledge

    def build(
        self,
        champion: str,
        role: str,
        enemy: str | None = None,
        puuid: str | None = None,
    ) -> ChampionContext:
        """
        Construye el contexto completo de un campeón para la UI.

        GI-1: carga perfil y matchup si existen. Devuelve contexto vacío si no.
        GI-3+: añade análisis estadístico, patrones, prioridades.
        GI-5+: añade learning state y drill activo.
        GI-7+: añade review enriquecida.
        """
        slug  = champion.lower()
        profile = self.knowledge.champion.get(slug)
        matchup = (
            self.knowledge.champion.get_matchup(slug, enemy.lower(), role)
            if enemy else None
        )

        return ChampionContext(
            champion         = slug,
            role             = role,
            has_profile      = profile is not None,
            has_matchup_profile = matchup is not None,
            profile          = profile,
            matchup_profile  = matchup,
        )

    def review(
        self,
        champion: str,
        role: str,
        match: dict,
        champion_history: list[dict] | None = None,
        enemy: str | None = None,
    ) -> EnrichedReview | None:
        """
        Review post-partida enriquecida con contexto de campeón y matchup.
        GI-7: implementación completa con ReviewIntelligenceEngine.
        """
        return None

    def learning(self, champion: str, role: str, puuid: str) -> LearningState | None:
        """
        Estado de aprendizaje del jugador en el campeón.
        GI-5: implementación completa con LearningIntelligenceEngine.
        """
        return None

    def training(self, champion: str, role: str, puuid: str) -> ActiveDrill | None:
        """
        Drill activo para el campeón.
        GI-6: implementación completa con TrainingIntelligenceEngine.
        """
        return None

    def available_champions(self) -> list[str]:
        """Lista de campeones con perfil disponible."""
        return self.knowledge.champion.list_available()

    def warm(self) -> dict:
        """Calienta todos los caches. Llamar al iniciar la app."""
        return self.knowledge.warm_all()
