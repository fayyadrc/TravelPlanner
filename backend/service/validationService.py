from typing import Dict, Any, List

# Minimum acceptable budget utilization
MIN_BUDGET_UTILIZATION = 0.80
MIN_HOURS_PER_DAY = 6.0


def validate_plan(plan: Dict[str, Any]) -> List[str]:
    """
    Validate plan quality after generation.

    Runs post-hoc checks and returns a list of quality warnings.
    These are separate from operational warnings (e.g., "no flights found")
    and focus on overall plan quality.

    Checks:
    1. Flights exist
    2. No duplicate activity IDs across days
    3. Budget utilization >= 80%
    4. Each day has >= MIN_HOURS_PER_DAY hours
    5. Hotel exists
    """
    quality_warnings = []

    # --- Check 1: Flights exist ---
    if not plan.get("flights"):
        quality_warnings.append(
            "⚠️ Quality: No flights in the plan — the itinerary may not be actionable."
        )

    # --- Check 2: No duplicate activities ---
    seen_ids = set()
    duplicates = set()
    for day in plan.get("itinerary", []):
        for activity in day.get("activities", []):
            aid = activity.get("id", "")
            # Skip placeholder activities
            if aid.startswith("FREE-"):
                continue
            if aid in seen_ids:
                duplicates.add(aid)
            seen_ids.add(aid)

    if duplicates:
        quality_warnings.append(
            f"⚠️ Quality: Duplicate activities detected across days: {', '.join(sorted(duplicates))}. "
            "Each activity should appear only once per trip."
        )

    # --- Check 3: Budget utilization ---
    total_cost = plan.get("total_cost", 0)
    budget = plan.get("budget", 1)
    utilization = total_cost / budget if budget > 0 else 0

    if utilization < MIN_BUDGET_UTILIZATION:
        quality_warnings.append(
            f"⚠️ Quality: Budget utilization is {utilization:.0%} "
            f"(target: ≥{MIN_BUDGET_UTILIZATION:.0%}). "
            f"${plan.get('budget', 0) - total_cost:.0f} remains unused."
        )

    # --- Check 4: Daily hour constraints ---
    for day in plan.get("itinerary", []):
        day_hours = day.get("day_hours", 0)
        day_num = day.get("day", "?")
        if day_hours < MIN_HOURS_PER_DAY:
            quality_warnings.append(
                f"⚠️ Quality: Day {day_num} has only {day_hours:.1f}h of activities "
                f"(minimum: {MIN_HOURS_PER_DAY:.0f}h)."
            )

    # --- Check 5: Hotel exists ---
    if not plan.get("hotels"):
        quality_warnings.append(
            "⚠️ Quality: No hotel in the plan — accommodation is missing."
        )

    return quality_warnings
