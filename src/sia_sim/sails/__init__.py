"""Sails and Wardrobe Advisor package."""

from __future__ import annotations

from sia_sim.contracts.sails import (
    ALL_SAIL_IDS,
    SAIL_RULES_CATALOG_V1_1,
    EffectiveSailDefinition,
    HullType,
    ReefRecommendation,
    SailAdvisoryPayload,
    SailBaseDefinition,
    SailCategory,
    SailSuitability,
    SailSuitabilityStatus,
)
from sia_sim.sails.advisor import (
    evaluate_reefing_schedule,
    evaluate_sail_suitability,
    generate_sail_advisory,
    resolve_wardrobe_for_hull,
)

__all__ = [
    "ALL_SAIL_IDS",
    "EffectiveSailDefinition",
    "HullType",
    "ReefRecommendation",
    "SAIL_RULES_CATALOG_V1_1",
    "SailAdvisoryPayload",
    "SailBaseDefinition",
    "SailCategory",
    "SailSuitability",
    "SailSuitabilityStatus",
    "evaluate_reefing_schedule",
    "evaluate_sail_suitability",
    "generate_sail_advisory",
    "resolve_wardrobe_for_hull",
]
