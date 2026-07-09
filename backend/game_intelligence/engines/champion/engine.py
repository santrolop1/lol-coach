"""
ChampionIntelligenceEngine — MVP.

Responsabilidad única: analizar las partidas de un jugador en un campeón específico
usando el perfil de conocimiento de ese campeón para generar un ChampionAnalysis.

PRINCIPIOS:
  - Nunca if champion == "X". Todo es genérico, leído desde el perfil.
  - No analiza wave, macro ni matchups (eso son otros motores).
  - No usa IA generativa.
  - Degradación elegante: funciona sin perfil (análisis estadístico puro).

ENTRADAS:
  champion: str               ← slug del campeón
  role: str
  scored_matches: list[dict]  ← partidas con scores (de scorer_v2)
  raw_matches: list[dict]     ← datos crudos de la tabla match

SALIDA:
  ChampionAnalysis
"""

from __future__ import annotations
import logging
from statistics import mean

from ...models.analysis import ChampionAnalysis, LiveCoachHints, DetectedMistake
from ...models.champion import PowerSpike

logger = logging.getLogger(__name__)

# Umbrales de confianza según número de partidas
_CONFIDENCE_THRESHOLDS = {
    "insufficient": 0,
    "low": 5,
    "medium": 15,
    "high": 30,
}


class ChampionIntelligenceEngine:
    """
    Motor de inteligencia de campeón.

    Acepta KnowledgeAPI como dependencia de inyección.
    Nunca importa directamente desde knowledge/.
    """

    def __init__(self, knowledge_api) -> None:
        self._k = knowledge_api

    def analyze(
        self,
        champion: str,
        role: str,
        raw_matches: list[dict],
        scored_matches: list[dict] | None = None,
    ) -> ChampionAnalysis:
        """
        Punto de entrada principal.

        Args:
            champion: slug del campeón (e.g. "tryndamere")
            role: "TOP" | "MID" | "ADC" | etc.
            raw_matches: lista de dicts de la tabla match (filtrados por campeón y role)
            scored_matches: opcional, lista de match_scores de scorer_v2

        Returns:
            ChampionAnalysis completo
        """
        slug = champion.lower()
        profile = self._k.champion.get(slug)
        n = len(raw_matches)

        if n == 0:
            return ChampionAnalysis(
                champion=slug,
                role=role,
                has_profile=profile is not None,
                confidence="insufficient",
                message="Sin partidas con este campeón para analizar.",
            )

        confidence = self._compute_confidence(n)

        if profile is None:
            return self._analyze_without_profile(slug, role, raw_matches, confidence)

        return self._analyze_with_profile(
            slug, role, profile, raw_matches, scored_matches or [], confidence
        )

    # ── Análisis con perfil ───────────────────────────────────────────────────

    def _analyze_with_profile(
        self,
        slug: str,
        role: str,
        profile,
        raw_matches: list[dict],
        scored_matches: list[dict],
        confidence: str,
    ) -> ChampionAnalysis:
        stats = self._compute_stats(raw_matches)

        # Detectar errores del perfil en los datos
        detected_mistakes = self._detect_mistakes(profile, stats, raw_matches)
        # Power spikes relevantes ordenados por impacto
        power_spikes = self._rank_power_spikes(profile, stats)
        # Fortalezas que el jugador está realizando
        strengths_realized = self._assess_strengths(profile, stats)
        # Debilidades siendo explotadas
        weaknesses_exposed = self._assess_weaknesses(profile, stats)
        # Áreas de foco priorizadas
        focus_areas = self._compute_focus(detected_mistakes, weaknesses_exposed)

        # Build y runas recomendadas (análisis situacional básico)
        build_rec = self._recommend_build(profile, raw_matches)
        rune_rec = self._recommend_rune_page(profile, raw_matches)

        # Wave y macro priorities del perfil
        wave_priorities = list(profile.wave_config.preferred_technique_ids)
        macro_priorities = list(profile.macro_config.primary_pattern_ids)

        live_coach = self._build_live_coach_hints(
            profile, stats, power_spikes, build_rec, rune_rec
        )

        return ChampionAnalysis(
            champion=slug,
            role=role,
            has_profile=True,
            strengths_realized=strengths_realized,
            weaknesses_exposed=weaknesses_exposed,
            detected_mistakes=detected_mistakes,
            power_spikes=power_spikes,
            focus_areas=focus_areas,
            build_recommendation=build_rec,
            rune_recommendation=rune_rec,
            wave_priorities=wave_priorities,
            macro_priorities=macro_priorities,
            live_coach=live_coach,
            confidence=confidence,
            games_analyzed=len(raw_matches),
        )

    def _analyze_without_profile(
        self,
        slug: str,
        role: str,
        raw_matches: list[dict],
        confidence: str,
    ) -> ChampionAnalysis:
        stats = self._compute_stats(raw_matches)
        focus = []
        if stats.get("deaths_avg", 0) > 5:
            focus.append("Reducir muertes — promedio actual muy alto.")
        if stats.get("cs_per_min", 0) < 5.5:
            focus.append("Mejorar CS/min — por debajo del promedio esperado.")
        if stats.get("kp", 0) < 0.40:
            focus.append("Aumentar participación en kills del equipo.")

        return ChampionAnalysis(
            champion=slug,
            role=role,
            has_profile=False,
            focus_areas=focus,
            confidence=confidence,
            games_analyzed=len(raw_matches),
            message=f"Sin perfil disponible para '{slug}'. Análisis estadístico puro.",
        )

    # ── Detección de errores ──────────────────────────────────────────────────

    def _detect_mistakes(
        self,
        profile,
        stats: dict,
        raw_matches: list[dict],
    ) -> list[DetectedMistake]:
        """
        Mapea estadísticas a los common_mistakes del perfil.
        Completamente genérico — lee del perfil, no if champion == X.
        """
        detected: list[DetectedMistake] = []

        deaths_avg = stats.get("deaths_avg", 0.0)
        cs_pm = stats.get("cs_per_min", 0.0)
        kp = stats.get("kp", 0.0)
        winrate = stats.get("winrate", 0.0)

        # Heurísticas genéricas basadas en fortalezas/debilidades del perfil
        # Un perfil de "late scaler" debería tener muchas muertes bajas
        if "scaling" in profile.playstyle and deaths_avg > 5:
            detected.append(DetectedMistake(
                mistake_text=(
                    "Morir demasiado en partidas de escalado — "
                    "este campeón necesita llegar a late game vivo."
                ),
                evidence=f"Promedio de muertes: {deaths_avg:.1f} (esperado < 4 para escaladores)",
                severity="high",
                games_observed=len(raw_matches),
            ))
        elif deaths_avg > 6:
            detected.append(DetectedMistake(
                mistake_text="Alto número de muertes por partida.",
                evidence=f"Promedio: {deaths_avg:.1f} muertes.",
                severity="high",
                games_observed=len(raw_matches),
            ))

        # CS por minuto bajo
        if cs_pm < 5.0:
            detected.append(DetectedMistake(
                mistake_text="CS/min muy bajo — se está perdiendo mucho farm.",
                evidence=f"CS/min: {cs_pm:.1f} (objetivo mínimo: 5.0)",
                severity="high" if cs_pm < 4.0 else "medium",
                games_observed=len(raw_matches),
            ))
        elif cs_pm < 6.5:
            detected.append(DetectedMistake(
                mistake_text="CS/min mejorable — hay espacio para optimizar el farm.",
                evidence=f"CS/min: {cs_pm:.1f} (objetivo óptimo: 7.0+)",
                severity="low",
                games_observed=len(raw_matches),
            ))

        # Además, añadir hasta 2 errores del perfil más genéricos si hay < 3 errores
        if len(detected) < 3 and profile.common_mistakes:
            # Siempre incluir el primer error del perfil si hay pocos errores detectados
            detected.append(DetectedMistake(
                mistake_text=profile.common_mistakes[0],
                evidence="Error más frecuente para este campeón según el perfil.",
                severity="medium",
                games_observed=0,  # no podemos verificarlo estadísticamente
            ))

        return detected[:5]  # máximo 5 errores para no abrumar

    # ── Power Spikes ─────────────────────────────────────────────────────────

    def _rank_power_spikes(
        self,
        profile,
        stats: dict,
    ) -> list[PowerSpike]:
        """Devuelve los power spikes del perfil ordenados por relevancia actual."""
        # Por ahora devolver todos los spikes — en GI-5+ se rankeará
        # según el estado actual de la partida o el tier del jugador
        return list(profile.power_spikes)

    # ── Fortalezas / debilidades ──────────────────────────────────────────────

    def _assess_strengths(self, profile, stats: dict) -> list[str]:
        """Fortalezas del campeón que el jugador parece estar aprovechando."""
        strengths = []
        winrate = stats.get("winrate", 0.0)
        if winrate >= 0.50 and profile.strengths:
            # Si gana partidas, asumimos que las fortalezas principales se realizan
            strengths.extend(profile.strengths[:2])
        return strengths

    def _assess_weaknesses(self, profile, stats: dict) -> list[str]:
        """Debilidades del campeón que están siendo explotadas en sus partidas."""
        exposed = []
        deaths_avg = stats.get("deaths_avg", 0.0)
        if deaths_avg > 4 and profile.weaknesses:
            # Si muere mucho, las debilidades early se están explotando
            exposed.extend(profile.weaknesses[:2])
        return exposed

    # ── Focus ─────────────────────────────────────────────────────────────────

    def _compute_focus(
        self,
        detected_mistakes: list[DetectedMistake],
        weaknesses_exposed: list[str],
    ) -> list[str]:
        """Top 3 áreas de mejora priorizadas por severidad."""
        high = [m.mistake_text for m in detected_mistakes if m.severity == "high"]
        medium = [m.mistake_text for m in detected_mistakes if m.severity == "medium"]
        areas = high + medium
        areas.extend(weaknesses_exposed)
        return list(dict.fromkeys(areas))[:3]  # dedup + top 3

    # ── Build y Runas ─────────────────────────────────────────────────────────

    def _recommend_build(self, profile, raw_matches: list[dict]) -> str:
        """
        Recomienda un build_id según el contexto de las partidas recientes.
        Por ahora: build estándar. GI-5 añade análisis de composiciones enemigas.
        """
        return profile.build_config.standard_build_id

    def _recommend_rune_page(self, profile, raw_matches: list[dict]) -> str:
        return profile.rune_config.standard_page_id

    # ── Live Coach Hints ──────────────────────────────────────────────────────

    def _build_live_coach_hints(
        self,
        profile,
        stats: dict,
        power_spikes: list[PowerSpike],
        build_rec: str,
        rune_rec: str,
    ) -> LiveCoachHints:
        next_spike = power_spikes[0] if power_spikes else None

        # Objetivo actual según el win condition del campeón
        win_cond_ids = profile.macro_config.win_condition_ids
        if "split_and_win" in win_cond_ids:
            current_objective = "Farmear, escalar, y split pushear cuando tengas 1-2 ítems."
        elif "teamfight_and_win" in win_cond_ids:
            current_objective = "Escalar y buscar peleas grupales en objetivos."
        else:
            current_objective = "Escalar y seguir el win condition del equipo."

        # Reminders genéricos del perfil
        reminders = []
        if profile.tips:
            reminders.append(profile.tips[0])
        if profile.common_mistakes:
            reminders.append(f"Evitar: {profile.common_mistakes[0][:60]}...")

        return LiveCoachHints(
            current_objective=current_objective,
            next_power_spike=next_spike,
            reminders=reminders,
            recommended_build_id=build_rec,
            recommended_rune_page_id=rune_rec,
            training_focus=profile.common_mistakes[0] if profile.common_mistakes else "",
        )

    # ── Estadísticas ──────────────────────────────────────────────────────────

    @staticmethod
    def _compute_stats(raw_matches: list[dict]) -> dict:
        """Calcula estadísticas agregadas de las partidas crudas."""
        if not raw_matches:
            return {}

        def avg(key: str) -> float:
            vals = [m.get(key, 0) or 0 for m in raw_matches]
            return mean(vals) if vals else 0.0

        def avg_ratio(num: str, den: str) -> float:
            ratios = []
            for m in raw_matches:
                d = m.get(den, 0) or 0
                if d > 0:
                    ratios.append((m.get(num, 0) or 0) / d)
            return mean(ratios) if ratios else 0.0

        wins = sum(1 for m in raw_matches if m.get("win"))
        return {
            "winrate": wins / len(raw_matches),
            "deaths_avg": avg("deaths"),
            "kills_avg": avg("kills"),
            "assists_avg": avg("assists"),
            "cs_per_min": avg("cs_per_min"),
            "damage_pm": avg("damage_per_min"),
            "kp": avg("kill_participation"),
            "vision_pm": avg("vision_score"),
            "gold_pm": avg("gold_per_min"),
        }

    @staticmethod
    def _compute_confidence(n: int) -> str:
        if n < _CONFIDENCE_THRESHOLDS["low"]:
            return "insufficient"
        if n < _CONFIDENCE_THRESHOLDS["medium"]:
            return "low"
        if n < _CONFIDENCE_THRESHOLDS["high"]:
            return "medium"
        return "high"
