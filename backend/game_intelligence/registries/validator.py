"""
ChampionValidator — validación profunda de perfiles de campeón.

Verifica no solo que los campos existen, sino que las referencias
a otros registries son válidas (builds, runas, waves, macro).
"""

from __future__ import annotations
import logging
from ..models.champion import ChampionProfile

logger = logging.getLogger(__name__)


class ChampionValidator:
    """
    Valida un ChampionProfile contra KnowledgeAPI.

    Uso:
        validator = ChampionValidator(knowledge)
        errors = validator.validate_full(profile)
        if errors:
            ...
    """

    def __init__(self, knowledge_api) -> None:
        self._k = knowledge_api

    def validate_full(self, profile: ChampionProfile) -> list[str]:
        """
        Validación completa: campos obligatorios + referencias cruzadas.
        Devuelve lista de errores. Lista vacía = perfil válido.
        """
        errors: list[str] = []
        errors.extend(self._validate_identity(profile))
        errors.extend(self._validate_abilities(profile))
        errors.extend(self._validate_build_config(profile))
        errors.extend(self._validate_rune_config(profile))
        errors.extend(self._validate_wave_config(profile))
        errors.extend(self._validate_macro_config(profile))
        errors.extend(self._validate_learning(profile))
        errors.extend(self._validate_combos(profile))
        errors.extend(self._validate_power_spikes(profile))
        return errors

    # ── Validadores privados ──────────────────────────────────────────────────

    def _validate_identity(self, p: ChampionProfile) -> list[str]:
        errors = []
        if not p.champion:
            errors.append("[identity] champion está vacío.")
        if not p.display_name:
            errors.append("[identity] display_name está vacío.")
        if not p.roles:
            errors.append("[identity] roles está vacío.")
        if not p.patch_version:
            errors.append("[identity] patch_version está vacío.")
        if not p.identity:
            errors.append("[identity] identity está vacío.")
        if not p.playstyle:
            errors.append("[identity] playstyle está vacío.")
        if not p.scaling:
            errors.append("[identity] scaling está vacío.")
        if not p.strengths:
            errors.append("[identity] strengths está vacío.")
        if not p.weaknesses:
            errors.append("[identity] weaknesses está vacío.")
        return errors

    def _validate_abilities(self, p: ChampionProfile) -> list[str]:
        errors = []
        if not p.abilities:
            errors.append("[abilities] No hay habilidades definidas.")
            return errors
        for key in ("P", "Q", "W", "E", "R"):
            if key not in p.abilities:
                errors.append(f"[abilities] Falta la habilidad '{key}'.")
            else:
                ab = p.abilities[key]
                if not ab.name:
                    errors.append(f"[abilities.{key}] name está vacío.")
                if not ab.description:
                    errors.append(f"[abilities.{key}] description está vacío.")
        return errors

    def _validate_build_config(self, p: ChampionProfile) -> list[str]:
        errors = []
        bc = p.build_config
        if not bc.standard_build_id:
            errors.append("[build_config] standard_build_id está vacío.")
            return errors
        # Verificar que el build existe en ItemRegistry
        if not self._k.item.get_build(bc.standard_build_id):
            errors.append(
                f"[build_config] standard_build_id '{bc.standard_build_id}' "
                f"no encontrado en ItemRegistry."
            )
        if bc.vs_tanks_build_id and not self._k.item.get_build(bc.vs_tanks_build_id):
            errors.append(
                f"[build_config] vs_tanks_build_id '{bc.vs_tanks_build_id}' "
                f"no encontrado en ItemRegistry."
            )
        if bc.vs_poke_build_id and not self._k.item.get_build(bc.vs_poke_build_id):
            errors.append(
                f"[build_config] vs_poke_build_id '{bc.vs_poke_build_id}' "
                f"no encontrado en ItemRegistry."
            )
        return errors

    def _validate_rune_config(self, p: ChampionProfile) -> list[str]:
        errors = []
        rc = p.rune_config
        if not rc.standard_page_id:
            errors.append("[rune_config] standard_page_id está vacío.")
            return errors
        if not self._k.rune.get(rc.standard_page_id):
            errors.append(
                f"[rune_config] standard_page_id '{rc.standard_page_id}' "
                f"no encontrado en RuneRegistry."
            )
        if rc.vs_poke_page_id and not self._k.rune.get(rc.vs_poke_page_id):
            errors.append(
                f"[rune_config] vs_poke_page_id '{rc.vs_poke_page_id}' "
                f"no encontrado en RuneRegistry."
            )
        return errors

    def _validate_wave_config(self, p: ChampionProfile) -> list[str]:
        errors = []
        wc = p.wave_config
        for wid in wc.preferred_technique_ids:
            if not self._k.wave.get(wid):
                errors.append(
                    f"[wave_config] técnica '{wid}' no encontrada en WaveRegistry."
                )
        if (
            wc.recall_setup_technique_id
            and not self._k.wave.get(wc.recall_setup_technique_id)
        ):
            errors.append(
                f"[wave_config] recall_setup_technique_id '{wc.recall_setup_technique_id}' "
                f"no encontrado en WaveRegistry."
            )
        return errors

    def _validate_macro_config(self, p: ChampionProfile) -> list[str]:
        errors = []
        mc = p.macro_config
        for pid in mc.primary_pattern_ids:
            if not self._k.macro.get(pid):
                errors.append(
                    f"[macro_config] patrón '{pid}' no encontrado en MacroRegistry."
                )
        for wcid in mc.win_condition_ids:
            if not self._k.macro.get_win_condition(wcid):
                errors.append(
                    f"[macro_config] win_condition '{wcid}' no encontrada en MacroRegistry."
                )
        return errors

    def _validate_learning(self, p: ChampionProfile) -> list[str]:
        errors = []
        if not p.learning_roadmap_id:
            errors.append("[learning] learning_roadmap_id está vacío.")
        return errors

    def _validate_combos(self, p: ChampionProfile) -> list[str]:
        errors = []
        if not p.combos:
            errors.append("[combos] No hay combos definidos.")
        seen_ids = set()
        for combo in p.combos:
            if combo.id in seen_ids:
                errors.append(f"[combos] ID duplicado: '{combo.id}'.")
            seen_ids.add(combo.id)
            if not combo.name:
                errors.append(f"[combos.{combo.id}] name está vacío.")
        return errors

    def _validate_power_spikes(self, p: ChampionProfile) -> list[str]:
        errors = []
        if not p.power_spikes:
            errors.append("[power_spikes] No hay power spikes definidos.")
        seen_ids = set()
        for spike in p.power_spikes:
            if spike.id in seen_ids:
                errors.append(f"[power_spikes] ID duplicado: '{spike.id}'.")
            seen_ids.add(spike.id)
        return errors
