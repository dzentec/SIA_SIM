"""Sail Rules v1.1 Data Contracts and Universal Wardrobe Catalog.

Provides strict Pydantic v2 schemas and canonical rules for monohulls and catamarans,
including wind ranges, optimal/marginal TWA sectors, max gust limits, and reefing schedules.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

HullType = Literal["monohull", "catamaran"]


class SailCategory(StrEnum):
    MAIN = "Main"
    HEADSAIL = "Headsail"
    DOWNWIND_REACHING = "Downwind / Reaching"
    DOWNWIND = "Downwind"
    REACHING = "Reaching"
    STORM = "Storm"


class SailSuitabilityStatus(StrEnum):
    OPTIMAL = "OPTIMAL"  # Ideal working sector (Score >= 0.85)
    MARGINAL = "MARGINAL"  # Acceptable with reduced aerodynamic efficiency (Score ~ 0.50)
    UNSUITABLE = "UNSUITABLE"  # Out of wind/angle bounds (Score = 0.0)
    DANGEROUS = "DANGEROUS"  # Wind or gust exceeds safety limits (Safety hazard)


class ReefRecommendation(BaseModel):
    """Reefing wind speed threshold for mainsails."""

    model_config = ConfigDict(frozen=True, strict=True)

    reef: int = Field(ge=1, le=4, description="Reef step (1, 2, 3, 4)")
    wind_speed_kt: float = Field(gt=0.0, description="Wind speed threshold in knots")


class SailBaseDefinition(BaseModel):
    """Base specification of a sail in the universal catalog."""

    model_config = ConfigDict(frozen=True, strict=True)

    id: str
    name: str
    category: str
    type: str
    compatible_hull_types: tuple[HullType, ...]
    wind_speed_range_kt: tuple[float, float]
    optimal_twa_range_deg: tuple[float, float]
    marginal_twa_range_deg: tuple[float, float]
    modern_status: str
    max_gust_kt: float | None = None
    reef_recommendations_kt: tuple[ReefRecommendation, ...] = ()
    priority: str = "normal"  # "normal" | "high"
    description: str


class EffectiveSailDefinition(SailBaseDefinition):
    """Resolved sail definition with hull-specific overrides applied."""

    hull_type: HullType
    profile_note: str | None = None


class SailSuitability(BaseModel):
    """Evaluation score and status for a single sail."""

    model_config = ConfigDict(frozen=True, strict=True)

    sail_id: str
    name: str
    category: str
    status: SailSuitabilityStatus
    score: float = Field(ge=0.0, le=1.0)
    is_available_on_board: bool = True
    recommended_action: str | None = None
    reason: str


class SailAdvisoryPayload(BaseModel):
    """Structured advisory response for cockpit display and SIA decision loop."""

    model_config = ConfigDict(frozen=True, strict=True)

    hull_type: HullType
    tws_kt: float
    twa_deg: float
    gust_kt: float | None = None
    recommended_main: str | None = None
    recommended_headsail: str | None = None
    recommended_reef: int = 0
    optimal_sails: tuple[str, ...] = ()
    marginal_sails: tuple[str, ...] = ()
    dangerous_sails: tuple[str, ...] = ()
    all_evaluations: tuple[SailSuitability, ...] = ()
    advisory_note: str = ""


# ---------------------------------------------------------------------------
# Canonical Catalog Data v1.1
# ---------------------------------------------------------------------------

SAIL_RULES_CATALOG_V1_1: dict[str, Any] = {
    "schema_version": "1.1",
    "title": "Универсальный справочник парусов для монокорпусных яхт и катамаранов",
    "description": "Единый каталог парусов с базовыми параметрами и профилями использования для разных типов корпуса. Учитывает специфику вымпельного ветра и порывов.",
    "units": {
        "wind_speed": "kt",
        "angle": "deg",
        "wind_angle_type": "TWA",
    },
    "hull_types": ["monohull", "catamaran"],
    "profiles": {
        "monohull": {
            "label": "Однокорпусная яхта",
            "global_notes": "Монокорпусная яхта может частично сбрасывать нагрузку креном, поэтому лимиты по ветру обычно могут быть шире, чем у катамарана.",
            "sail_overrides": {
                "genoa_furling": {
                    "wind_speed_range_kt": [6, 22],
                    "note": "На монокорпусе генуя может использоваться немного дольше, чем на катамаране, но при усилении ветра её нужно закручивать.",
                },
            },
        },
        "catamaran": {
            "label": "Катамаран",
            "global_notes": "Катамаран почти не кренится, поэтому площадь парусов нужно уменьшать раньше. Из-за высокой скорости вымпельный ветер (AWA) сильно уходит на нос. Ходить чистым фордевиндом (TWA 180°) не рекомендуется из-за риска случайного джайба, схлопывания парусов и потери скорости.",
            "sail_overrides": {
                "mainsail_square_top": {
                    "wind_speed_range_kt": [0, 30],
                    "note": "На катамаране грот является основным парусом. Рифы рекомендуется брать раньше, чем на монокорпусе.",
                    "reef_recommendations_kt": [
                        {"reef": 1, "wind_speed_kt": 15},
                        {"reef": 2, "wind_speed_kt": 20},
                        {"reef": 3, "wind_speed_kt": 25},
                    ],
                },
                "solent_jib": {
                    "wind_speed_range_kt": [12, 28],
                    "note": "В свежем ветре на катамаране лучше уменьшать площадь раньше и использовать грот с рифами.",
                },
                "genoa_furling": {
                    "wind_speed_range_kt": [6, 18],
                    "max_gust_kt": 22,
                    "note": "На катамаране геную лучше убирать или сильно закручивать раньше, чтобы не перегружать судно. Опасайтесь порывов.",
                },
                "code_zero": {
                    "wind_speed_range_kt": [4, 14],
                    "max_gust_kt": 18,
                    "note": "Code 0 очень полезен на катамаране в слабый ветер, но в свежем ветру и при порывах его нужно использовать крайне осторожно.",
                },
                "asymmetric_gennaker_a2": {
                    "wind_speed_range_kt": [6, 18],
                    "max_gust_kt": 22,
                    "optimal_twa_range_deg": [110, 150],
                    "note": "Лёгкий попутный парус. Не рекомендуется ходить на углах >150° (чистый фордевинд) во избежание схлопывания и потери скорости. Перегрузка наступает раньше.",
                },
                "asymmetric_gennaker_a3": {
                    "wind_speed_range_kt": [14, 24],
                    "max_gust_kt": 28,
                    "note": "Для катамарана нужен прочный бушприт и контроль угла атаки.",
                },
                "parasailor": {
                    "wind_speed_range_kt": [8, 28],
                    "optimal_twa_range_deg": [120, 160],
                    "priority": "high",
                    "note": "Очень полезен на катамаране на полных курсах: стабилизирует курс и уменьшает зарывание носов. Избегайте чистого фордевинда (180°).",
                },
                "storm_jib": {
                    "wind_speed_range_kt": [28, 50],
                    "note": "Для офшорного катамарана желательно размещение на внутреннем съёмном штаге или прочном штормовом штаге.",
                },
            },
        },
    },
    "sails": [
        {
            "id": "mainsail_square_top",
            "name": "Грот (Square-Top Mainsail)",
            "category": "Main",
            "type": "Primary",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [0, 35],
            "optimal_twa_range_deg": [30, 180],
            "marginal_twa_range_deg": [20, 30],
            "modern_status": "Standard",
            "reef_recommendations_kt": [
                {"reef": 1, "wind_speed_kt": 18},
                {"reef": 2, "wind_speed_kt": 25},
                {"reef": 3, "wind_speed_kt": 32},
            ],
            "description": "Основной несущий парус с прямоугольной верхней частью. Используется почти на всех курсах. Площадь регулируется рифлением.",
        },
        {
            "id": "solent_jib",
            "name": "Солент / Самоповоротный стаксель (Solent / Self-tacking Jib)",
            "category": "Headsail",
            "type": "Upwind",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [12, 30],
            "optimal_twa_range_deg": [30, 60],
            "marginal_twa_range_deg": [60, 90],
            "modern_status": "Standard",
            "description": "Основной лавировочный парус для острых курсов и среднего/сильного ветра. Часто монтируется на стационарном или съёмном штаге. На катамаранах может использоваться на внутреннем штаге.",
        },
        {
            "id": "genoa_furling",
            "name": "Универсальная генуя (Roller Furling Genoa)",
            "category": "Headsail",
            "type": "All-round",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [6, 20],
            "optimal_twa_range_deg": [40, 110],
            "marginal_twa_range_deg": [110, 140],
            "modern_status": "Standard",
            "description": "Заменяет устаревший набор «Генуя 1-2-3». Перекрывает мачту, площадь регулируется закруткой.",
        },
        {
            "id": "code_zero",
            "name": "Код 0 (Code 0)",
            "category": "Downwind / Reaching",
            "type": "Light Wind Reacher",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [4, 15],
            "optimal_twa_range_deg": [45, 90],
            "marginal_twa_range_deg": [90, 120],
            "modern_status": "Popular",
            "description": "Гибрид стакселя и геннакера на гибком штаге с закруткой. Особенно полезен на катамаранах в слабый ветер.",
        },
        {
            "id": "asymmetric_gennaker_a2",
            "name": "Асимметричный геннакер A2 (Runner)",
            "category": "Downwind",
            "type": "Light/Medium Downwind",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [6, 20],
            "optimal_twa_range_deg": [120, 165],
            "marginal_twa_range_deg": [110, 120],
            "modern_status": "Standard",
            "description": "Глубокий попутный парус большой площади. Не требует спинакер-гика, ставится на бушприт.",
        },
        {
            "id": "asymmetric_gennaker_a3",
            "name": "Асимметричный геннакер A3/A5 (Reacher)",
            "category": "Reaching",
            "type": "Heavy/Medium Reaching",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [14, 25],
            "optimal_twa_range_deg": [80, 130],
            "marginal_twa_range_deg": [70, 80],
            "modern_status": "Popular",
            "description": "Более плоский и прочный асимметричный парус для силового галфвинда и бакштага.",
        },
        {
            "id": "parasailor",
            "name": "Парасейлор / Крылатый спинакер (Parasailor)",
            "category": "Downwind",
            "type": "Cruising Downwind",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [8, 28],
            "optimal_twa_range_deg": [130, 180],
            "marginal_twa_range_deg": [110, 130],
            "modern_status": "Cruising Standard",
            "description": "Современный парус для круизных яхт и катамаранов со встроенным крылом-аэродинамическим профилем. Гасит качку, стабилизирует нос и уменьшает рыскание на полных курсах.",
        },
        {
            "id": "storm_jib",
            "name": "Штормовой стаксель (Storm Jib / Storm Staysail)",
            "category": "Storm",
            "type": "Survival",
            "compatible_hull_types": ["monohull", "catamaran"],
            "wind_speed_range_kt": [28, 50],
            "optimal_twa_range_deg": [35, 140],
            "marginal_twa_range_deg": [30, 35],
            "modern_status": "Mandatory Safety",
            "description": "Маленький плоский парус из сверхпрочной ткани для тяжёлых штормовых условий. На офшорных катамаранах часто ставится на внутренний съёмный штаг.",
        },
    ],
}

class CanonicalSailId(StrEnum):
    """Canonical unique identifiers for all sails across SIA Core, Simulation, and Rig physics."""

    MAINSAIL_SQUARE_TOP = "mainsail_square_top"
    SOLENT_JIB = "solent_jib"
    GENOA_FURLING = "genoa_furling"
    CODE_ZERO = "code_zero"
    ASYMMETRIC_GENNAKER_A2 = "asymmetric_gennaker_a2"
    ASYMMETRIC_GENNAKER_A3 = "asymmetric_gennaker_a3"
    PARASAILOR = "parasailor"
    STORM_JIB = "storm_jib"


ALL_SAIL_IDS: tuple[str, ...] = tuple(s.value for s in CanonicalSailId)


CANONICAL_SAIL_NAMES_RU: dict[str, str] = {
    CanonicalSailId.MAINSAIL_SQUARE_TOP: "Грот (Square-Top Mainsail)",
    CanonicalSailId.SOLENT_JIB: "Солент / Самоповоротный стаксель (Solent Jib)",
    CanonicalSailId.GENOA_FURLING: "Генуя на закрутке (Furling Genoa)",
    CanonicalSailId.CODE_ZERO: "Код 0 (Code 0)",
    CanonicalSailId.ASYMMETRIC_GENNAKER_A2: "Асимметричный геннакер A2 (Runner)",
    CanonicalSailId.ASYMMETRIC_GENNAKER_A3: "Асимметричный геннакер A3 (Reacher)",
    CanonicalSailId.PARASAILOR: "Парасейлор (Parasailor)",
    CanonicalSailId.STORM_JIB: "Штормовой стаксель (Storm Jib)",
}

