"""Sail Advisor Engine for SIA Simulation.

Evaluates sail suitability, gust safety limits, reefing schedules, and generates
advisory payloads strictly constrained to on-board available sail inventory.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sia_sim.contracts.sails import (
    ALL_SAIL_IDS,
    SAIL_RULES_CATALOG_V1_1,
    EffectiveSailDefinition,
    HullType,
    ReefRecommendation,
    SailAdvisoryPayload,
    SailSuitability,
    SailSuitabilityStatus,
)


def resolve_wardrobe_for_hull(hull_type: str = "monohull") -> dict[str, EffectiveSailDefinition]:
    """Resolves base sail catalog with hull-specific overrides (monohull or catamaran)."""
    h_type: HullType = "catamaran" if "cat" in hull_type.lower() else "monohull"
    profiles = SAIL_RULES_CATALOG_V1_1.get("profiles", {})
    profile = profiles.get(h_type, {})
    overrides = profile.get("sail_overrides", {})

    resolved: dict[str, EffectiveSailDefinition] = {}

    for base_dict in SAIL_RULES_CATALOG_V1_1.get("sails", []):
        sail_id = base_dict["id"]
        merged: dict[str, Any] = dict(base_dict)
        profile_note: str | None = None

        if sail_id in overrides:
            ov = overrides[sail_id]
            profile_note = ov.get("note")
            for k, v in ov.items():
                if k != "note":
                    merged[k] = v

        # Convert lists to immutable tuples
        merged["wind_speed_range_kt"] = (
            float(merged["wind_speed_range_kt"][0]),
            float(merged["wind_speed_range_kt"][1]),
        )
        merged["optimal_twa_range_deg"] = (
            float(merged["optimal_twa_range_deg"][0]),
            float(merged["optimal_twa_range_deg"][1]),
        )
        merged["marginal_twa_range_deg"] = (
            float(merged["marginal_twa_range_deg"][0]),
            float(merged["marginal_twa_range_deg"][1]),
        )
        merged["compatible_hull_types"] = tuple(merged["compatible_hull_types"])

        reef_recs: list[ReefRecommendation] = []
        for r in merged.get("reef_recommendations_kt", []):
            if isinstance(r, dict):
                reef_recs.append(ReefRecommendation(reef=int(r["reef"]), wind_speed_kt=float(r["wind_speed_kt"])))
            elif isinstance(r, ReefRecommendation):
                reef_recs.append(r)
        merged["reef_recommendations_kt"] = tuple(reef_recs)

        resolved[sail_id] = EffectiveSailDefinition(
            **merged,
            hull_type=h_type,
            profile_note=profile_note,
        )

    return resolved


def evaluate_sail_suitability(
    sail: EffectiveSailDefinition,
    tws_kt: float,
    twa_deg: float,
    gust_kt: float | None = None,
    is_available: bool = True,
) -> SailSuitability:
    """Evaluate suitability of a single sail in given wind conditions."""
    abs_twa = abs(twa_deg) % 360.0
    if abs_twa > 180.0:
        abs_twa = 360.0 - abs_twa

    min_tws, max_tws = sail.wind_speed_range_kt
    opt_twa_min, opt_twa_max = sail.optimal_twa_range_deg
    marg_twa_min, marg_twa_max = sail.marginal_twa_range_deg

    # 1. Check max gust safety threshold
    effective_gust = gust_kt if gust_kt is not None else tws_kt
    if sail.max_gust_kt is not None and effective_gust > sail.max_gust_kt:
        return SailSuitability(
            sail_id=sail.id,
            name=sail.name,
            category=sail.category,
            status=SailSuitabilityStatus.DANGEROUS,
            score=0.0,
            is_available_on_board=is_available,
            recommended_action=f"Убрать / закрутить {sail.name}",
            reason=f"Порыв ветра {effective_gust:.1f} kt превышает лимит прочности/остойчивости ({sail.max_gust_kt} kt)",
        )

    # 2. Check maximum sustained wind speed (Over-range safety hazard)
    if tws_kt > max_tws:
        return SailSuitability(
            sail_id=sail.id,
            name=sail.name,
            category=sail.category,
            status=SailSuitabilityStatus.DANGEROUS,
            score=0.0,
            is_available_on_board=is_available,
            recommended_action=f"Убрать {sail.name}",
            reason=f"Ветер {tws_kt:.1f} kt превышает допустимый максимум ({max_tws} kt) — риск перегрузки и брочинга",
        )

    # 3. Check minimum wind speed
    if tws_kt < min_tws:
        return SailSuitability(
            sail_id=sail.id,
            name=sail.name,
            category=sail.category,
            status=SailSuitabilityStatus.UNSUITABLE,
            score=0.10,
            is_available_on_board=is_available,
            recommended_action=None,
            reason=f"Слишком слабый ветер ({tws_kt:.1f} kt < {min_tws} kt) — парус не наполнится",
        )

    # 4. Check Catamaran dead-downwind hazard (accidental gybe / collapse)
    if (
        sail.hull_type == "catamaran"
        and sail.id in ("asymmetric_gennaker_a2", "parasailor")
        and abs_twa > opt_twa_max
        and abs_twa >= 165.0
    ):
        return SailSuitability(
            sail_id=sail.id,
            name=sail.name,
            category=sail.category,
            status=SailSuitabilityStatus.MARGINAL,
            score=0.40,
            is_available_on_board=is_available,
            recommended_action=f"Увалиться/привестись до TWA {opt_twa_max:.0f}°",
            reason=f"Чистый фордевинд (TWA {abs_twa:.0f}°) на катамаране опасен схлопыванием и потерей скорости",
        )

    # 5. Check TWA Angle ranges
    is_optimal_twa = opt_twa_min <= abs_twa <= opt_twa_max
    is_marginal_twa = marg_twa_min <= abs_twa <= marg_twa_max

    if is_optimal_twa:
        base_score = 0.95 if sail.priority != "high" else 1.0
        return SailSuitability(
            sail_id=sail.id,
            name=sail.name,
            category=sail.category,
            status=SailSuitabilityStatus.OPTIMAL,
            score=base_score,
            is_available_on_board=is_available,
            recommended_action=f"Нести {sail.name}",
            reason=f"Идеальный сектор: TWA {abs_twa:.0f}° при TWS {tws_kt:.1f} kt",
        )
    elif is_marginal_twa:
        return SailSuitability(
            sail_id=sail.id,
            name=sail.name,
            category=sail.category,
            status=SailSuitabilityStatus.MARGINAL,
            score=0.55,
            is_available_on_board=is_available,
            recommended_action=f"Допустимо ({sail.name})",
            reason=f"Пограничный угол TWA {abs_twa:.0f}° — сниженная эффективность",
        )
    else:
        return SailSuitability(
            sail_id=sail.id,
            name=sail.name,
            category=sail.category,
            status=SailSuitabilityStatus.UNSUITABLE,
            score=0.0,
            is_available_on_board=is_available,
            recommended_action=None,
            reason=f"Курс TWA {abs_twa:.0f}° вне аэродинамического сектора паруса",
        )


def evaluate_reefing_schedule(
    mainsail: EffectiveSailDefinition,
    tws_kt: float,
) -> tuple[int, str]:
    """Calculates recommended reef step (0, 1, 2, 3) for mainsail based on TWS."""
    if not mainsail.reef_recommendations_kt:
        # Default heuristics for standard monohull if not specified
        if tws_kt >= 32.0:
            return 3, "Рекомендуется 3-й риф (TWS ≥ 32 kt)"
        elif tws_kt >= 24.0:
            return 2, "Рекомендуется 2-й риф (TWS ≥ 24 kt)"
        elif tws_kt >= 18.0:
            return 1, "Рекомендуется 1-й риф (TWS ≥ 18 kt)"
        return 0, "Полный грот (Full Main)"

    # Sorted by reef number descending
    sorted_reefs = sorted(mainsail.reef_recommendations_kt, key=lambda r: r.reef, reverse=True)
    for r in sorted_reefs:
        if tws_kt >= r.wind_speed_kt:
            return r.reef, f"Рекомендуется {r.reef}-й риф (TWS ≥ {r.wind_speed_kt:.0f} kt)"

    return 0, "Полный грот (Full Main)"


def generate_sail_advisory(
    tws_kt: float,
    twa_deg: float,
    hull_type: str = "monohull",
    available_sails: Sequence[str] | None = None,
    gust_kt: float | None = None,
    active_sail_plan: str | None = None,
) -> SailAdvisoryPayload:
    """Generates complete SailAdvisoryPayload strictly filtering by available on-board sails."""
    wardrobe = resolve_wardrobe_for_hull(hull_type)
    avail_set = set(available_sails) if available_sails is not None else set(ALL_SAIL_IDS)

    evaluations: list[SailSuitability] = []
    optimal_list: list[str] = []
    marginal_list: list[str] = []
    dangerous_list: list[str] = []

    best_headsail: str | None = None
    best_headsail_score: float = -1.0

    best_main: str | None = None
    best_main_score: float = -1.0

    for sail_id, sail_def in wardrobe.items():
        is_avail = sail_id in avail_set
        suit = evaluate_sail_suitability(
            sail=sail_def,
            tws_kt=tws_kt,
            twa_deg=twa_deg,
            gust_kt=gust_kt,
            is_available=is_avail,
        )
        evaluations.append(suit)

        if suit.status == SailSuitabilityStatus.DANGEROUS:
            dangerous_list.append(sail_id)
        elif suit.status == SailSuitabilityStatus.OPTIMAL and is_avail:
            optimal_list.append(sail_id)
        elif suit.status == SailSuitabilityStatus.MARGINAL and is_avail:
            marginal_list.append(sail_id)

        # Pick best headsail/downwind sail strictly among available
        if is_avail and suit.status in (
            SailSuitabilityStatus.OPTIMAL,
            SailSuitabilityStatus.MARGINAL,
        ):
            if sail_def.category == "Main":
                if suit.score > best_main_score:
                    best_main_score = suit.score
                    best_main = sail_id
            else:
                if suit.score > best_headsail_score:
                    best_headsail_score = suit.score
                    best_headsail = sail_id

    # Fallback headsail among available if none optimal
    if best_headsail is None:
        if tws_kt >= 28.0 and "storm_jib" in avail_set:
            best_headsail = "storm_jib"
        elif "solent_jib" in avail_set:
            best_headsail = "solent_jib"
        elif "genoa_furling" in avail_set:
            best_headsail = "genoa_furling"

    # Evaluate reef step for mainsail
    main_def = wardrobe.get("mainsail_square_top")
    rec_reef = 0
    reef_note = ""
    if main_def is not None:
        rec_reef, reef_note = evaluate_reefing_schedule(main_def, tws_kt)

    # Build concise human note
    notes: list[str] = []
    if dangerous_list:
        dangerous_names = [wardrobe[s].name for s in dangerous_list if s in wardrobe]
        notes.append(f"⚠️ Опасность перегрузки: {', '.join(dangerous_names)}")
    if reef_note and rec_reef > 0:
        notes.append(f"⛵ {reef_note}")
    if best_headsail:
        notes.append(f"🎯 Оптимальный передний парус: {wardrobe[best_headsail].name}")

    return SailAdvisoryPayload(
        hull_type="catamaran" if "cat" in hull_type.lower() else "monohull",
        tws_kt=round(tws_kt, 2),
        twa_deg=round(twa_deg, 1),
        gust_kt=round(gust_kt, 2) if gust_kt is not None else None,
        recommended_main=best_main,
        recommended_headsail=best_headsail,
        recommended_reef=rec_reef,
        optimal_sails=tuple(optimal_list),
        marginal_sails=tuple(marginal_list),
        dangerous_sails=tuple(dangerous_list),
        all_evaluations=tuple(evaluations),
        advisory_note=" | ".join(notes) if notes else "Условия в пределах нормы",
    )
