import json
import os
from typing import List, Dict, Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/activities.json")

# How many hours are realistically usable per day for activities
AVAILABLE_HOURS_PER_DAY = 8.0

# Activity budget = 25% of total budget, split evenly across days
ACTIVITY_BUDGET_SHARE = 0.25

# Target activities per day
MIN_ACTIVITIES_PER_DAY = 2
MAX_ACTIVITIES_PER_DAY = 4


def load_activities() -> List[Dict[str, Any]]:
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def filter_by_destination(
    activities: List[Dict], destination: str
) -> List[Dict]:
    return [
        a for a in activities
        if a["destination"].lower() == destination.lower()
    ]


def score_activity(activity: Dict, preferences: List[str]) -> float:
    """
    Score an activity based on preference match.
    - Each matching preference tag adds 1.0 to the score
    - Free activities get a small bonus (good for budget trips)
    - Falls back to 0.5 for activities with no preference match
      so they still appear when preferences don't fully overlap
    """
    activity_types = [t.lower() for t in activity.get("type", [])]
    pref_lower = [p.lower() for p in preferences]

    match_score = sum(1.0 for p in pref_lower if p in activity_types)

    # Small bonus for free activities
    free_bonus = 0.3 if activity["cost"] == 0 else 0.0

    # If no match at all, give a baseline so the day isn't empty
    if match_score == 0:
        return 0.5 + free_bonus

    return match_score + free_bonus


def select_activities_for_day(
    candidates: List[Dict],
    used_ids: set,
    daily_budget: float,
    budget_spent_today: float,
) -> List[Dict]:
    """
    Greedily pick 2–4 activities for a single day.

    Rules:
    - Skip already used activities (no repeats across the trip)
    - Respect daily budget ceiling
    - Respect AVAILABLE_HOURS_PER_DAY
    - Stop at MAX_ACTIVITIES_PER_DAY
    - Mix time_of_day slots: prefer one morning + one afternoon/any + optional evening
    """
    selected = []
    hours_used = 0.0
    cost_used = budget_spent_today

    # Prefer a spread across time slots
    time_slot_order = ["morning", "afternoon", "any", "full-day", "evening"]
    # Track which slots have been filled
    slots_filled = set()

    # Sort candidates by score descending (already scored externally)
    available = [a for a in candidates if a["id"] not in used_ids]

    for slot in time_slot_order:
        if len(selected) >= MAX_ACTIVITIES_PER_DAY:
            break

        slot_candidates = [
            a for a in available
            if a["time_of_day"] == slot and a["id"] not in {s["id"] for s in selected}
        ]

        for activity in slot_candidates:
            if len(selected) >= MAX_ACTIVITIES_PER_DAY:
                break

            would_exceed_hours = hours_used + activity["duration_hours"] > AVAILABLE_HOURS_PER_DAY
            would_exceed_budget = cost_used + activity["cost"] > daily_budget

            # Full-day activities take the whole day — only allow if day is empty
            if activity["time_of_day"] == "full-day" and len(selected) > 0:
                continue

            if would_exceed_hours or would_exceed_budget:
                continue

            selected.append(activity)
            hours_used += activity["duration_hours"]
            cost_used += activity["cost"]
            slots_filled.add(slot)
            break  # Move to next slot after filling this one

    # If still under minimum, fill from any remaining regardless of slot
    if len(selected) < MIN_ACTIVITIES_PER_DAY:
        extras = [
            a for a in available
            if a["id"] not in {s["id"] for s in selected}
            and a["time_of_day"] != "full-day"
        ]
        for activity in extras:
            if len(selected) >= MIN_ACTIVITIES_PER_DAY:
                break
            if hours_used + activity["duration_hours"] > AVAILABLE_HOURS_PER_DAY:
                continue
            if cost_used + activity["cost"] > daily_budget:
                continue
            selected.append(activity)
            hours_used += activity["duration_hours"]
            cost_used += activity["cost"]

    return selected


def build_itinerary(
    destination: str,
    days: int,
    preferences: List[str],
    total_budget: float,
) -> Dict[str, Any]:

    """
    Build a day-by-day itinerary.

    Returns:
        {
            "itinerary": [
                {
                    "day": 1,
                    "activities": [...],
                    "day_cost": float,
                    "day_hours": float,
                }
            ],
            "total_activity_cost": float,
            "warnings": [...]
        }
    """
    warnings = []
    all_activities = load_activities()

    # Filter to destination
    candidates = filter_by_destination(all_activities, destination)

    if not candidates:
        warnings.append(f"No activities found for destination '{destination}'.")
        return {
            "itinerary": [],
            "total_activity_cost": 0.0,
            "warnings": warnings,
        }

    # Score and sort all candidates once
    scored = sorted(
        candidates,
        key=lambda a: score_activity(a, preferences),
        reverse=True,
    )

    # Budget allocation
    activity_budget_total = total_budget * ACTIVITY_BUDGET_SHARE
    daily_budget = activity_budget_total / days

    itinerary = []
    used_ids: set = set()
    total_activity_cost = 0.0

    for day_num in range(1, days + 1):
        day_activities = select_activities_for_day(
            candidates=scored,
            used_ids=used_ids,
            daily_budget=daily_budget,
            budget_spent_today=0.0,
        )

        # Dataset exhausted — reset used_ids and try again (long trips)
        if len(day_activities) < MIN_ACTIVITIES_PER_DAY and used_ids:
            used_ids.clear()
            day_activities = select_activities_for_day(
                candidates=scored,
                used_ids=used_ids,
                daily_budget=daily_budget,
                budget_spent_today=0.0,
            )
            if day_num == 1 or day_activities:
                warnings.append(
                    f"Day {day_num}: recycling activities — dataset doesn't have enough "
                    f"unique options for a {days}-day trip to {destination}."
                )

        if not day_activities:
            warnings.append(
                f"Day {day_num}: no activities fit within the daily budget of ${daily_budget:.0f}."
            )

        # Mark used
        for a in day_activities:
            used_ids.add(a["id"])

        day_cost = sum(a["cost"] for a in day_activities)
        day_hours = sum(a["duration_hours"] for a in day_activities)
        total_activity_cost += day_cost

        itinerary.append({
            "day": day_num,
            "activities": day_activities,
            "day_cost": round(day_cost, 2),
            "day_hours": round(day_hours, 1),
        })

    # Warn if we ran out of unique activities (trip longer than dataset covers)
    total_used = sum(len(d["activities"]) for d in itinerary)
    if total_used < days * MIN_ACTIVITIES_PER_DAY:
        warnings.append(
            "Some days have fewer than 2 activities — dataset may not have enough "
            f"variety for a {days}-day trip to {destination}."
        )

    return {
        "itinerary": itinerary,
        "total_activity_cost": round(total_activity_cost, 2),
        "warnings": warnings,
    }