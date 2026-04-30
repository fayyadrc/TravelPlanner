import json
import os
from typing import List, Dict, Any, Optional

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/activities.json")

# How many hours are realistically usable per day for activities
MAX_HOURS_PER_DAY = 8.0
MIN_HOURS_PER_DAY = 6.0

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


def area_bonus(activity: Dict, selected: List[Dict]) -> float:
    """
    Reward same-area activities, penalize area switches.
    Encourages geographically clustered itineraries.
    """
    if not selected:
        return 0.0
    last_area = selected[-1].get("area", "")
    if activity.get("area", "") == last_area:
        return 0.5  # Same area bonus
    return -0.2  # Area switch penalty


def make_free_exploration(day_num: int, slot_index: int, destination: str) -> Dict[str, Any]:
    """Create a Free Exploration placeholder activity."""
    return {
        "id": f"FREE-{day_num}-{slot_index}",
        "name": f"Free Exploration — {destination}",
        "type": ["leisure"],
        "duration_hours": 3.0,
        "cost": 0,
        "area": "Various",
        "time_of_day": "any",
        "description": f"Explore {destination} at your own pace — wander local streets, visit cafés, and soak in the atmosphere.",
        "is_placeholder": True,
    }


def select_activities_for_day(
    candidates: List[Dict],
    used_ids: set,
    daily_budget: float,
    budget_spent_today: float,
    preferences: List[str],
) -> List[Dict]:
    """
    Greedily pick 2–4 activities for a single day.

    Rules:
    - Skip already used activities (no repeats across the trip)
    - Respect daily budget ceiling
    - Respect MAX_HOURS_PER_DAY
    - Stop at MAX_ACTIVITIES_PER_DAY
    - Mix time_of_day slots: prefer one morning + one afternoon/any + optional evening
    - Prefer activities in the same geographic area (clustering)
    - Enforce MIN_HOURS_PER_DAY target
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

        # Sort by preference score + area bonus for geographic clustering
        slot_candidates.sort(
            key=lambda a: score_activity(a, preferences) + area_bonus(a, selected),
            reverse=True,
        )

        for activity in slot_candidates:
            if len(selected) >= MAX_ACTIVITIES_PER_DAY:
                break

            would_exceed_hours = hours_used + activity["duration_hours"] > MAX_HOURS_PER_DAY
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
        # Sort extras by area clustering too
        extras.sort(
            key=lambda a: score_activity(a, preferences) + area_bonus(a, selected),
            reverse=True,
        )
        for activity in extras:
            if len(selected) >= MIN_ACTIVITIES_PER_DAY:
                break
            if hours_used + activity["duration_hours"] > MAX_HOURS_PER_DAY:
                continue
            if cost_used + activity["cost"] > daily_budget:
                continue
            selected.append(activity)
            hours_used += activity["duration_hours"]
            cost_used += activity["cost"]

    # If still under MIN_HOURS_PER_DAY and we have room for more activities
    if hours_used < MIN_HOURS_PER_DAY and len(selected) < MAX_ACTIVITIES_PER_DAY:
        fillers = [
            a for a in available
            if a["id"] not in {s["id"] for s in selected}
            and a["time_of_day"] != "full-day"
        ]
        fillers.sort(
            key=lambda a: score_activity(a, preferences) + area_bonus(a, selected),
            reverse=True,
        )
        for activity in fillers:
            if hours_used >= MIN_HOURS_PER_DAY or len(selected) >= MAX_ACTIVITIES_PER_DAY:
                break
            if hours_used + activity["duration_hours"] > MAX_HOURS_PER_DAY:
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
    activity_budget_pct: float = ACTIVITY_BUDGET_SHARE,
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
    activity_budget_total = total_budget * activity_budget_pct
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
            preferences=preferences,
        )

        # If unique activities exhausted, fill with Free Exploration (no recycling)
        if len(day_activities) < MIN_ACTIVITIES_PER_DAY:
            shortage = MIN_ACTIVITIES_PER_DAY - len(day_activities)
            warnings.append(
                f"Day {day_num}: only {len(day_activities)} unique activity(ies) available — "
                f"adding {shortage} free exploration slot(s)."
            )
            while len(day_activities) < MIN_ACTIVITIES_PER_DAY:
                placeholder = make_free_exploration(
                    day_num, len(day_activities), destination
                )
                day_activities.append(placeholder)

        if not day_activities:
            warnings.append(
                f"Day {day_num}: no activities fit within the daily budget of ${daily_budget:.0f}."
            )

        # Mark used (skip placeholders)
        for a in day_activities:
            if not a.get("is_placeholder", False):
                used_ids.add(a["id"])

        day_cost = sum(a["cost"] for a in day_activities)
        day_hours = sum(a["duration_hours"] for a in day_activities)
        total_activity_cost += day_cost

        # Warn if day is still under minimum hours after all attempts
        if day_hours < MIN_HOURS_PER_DAY:
            warnings.append(
                f"Day {day_num}: only {day_hours:.1f}h of activities planned "
                f"(target: {MIN_HOURS_PER_DAY:.0f}h minimum)."
            )

        itinerary.append({
            "day": day_num,
            "activities": day_activities,
            "day_cost": round(day_cost, 2),
            "day_hours": round(day_hours, 1),
        })

    return {
        "itinerary": itinerary,
        "total_activity_cost": round(total_activity_cost, 2),
        "warnings": warnings,
    }


def find_additional_activities(
    destination: str,
    used_ids: set,
    remaining_budget: float,
    itinerary: List[Dict],
    preferences: List[str],
) -> List[Dict]:

    """
    Find activities to add to underpacked days for budget optimization.

    Placeholder (Free Exploration) hours are treated as replaceable — real
    activities can displace them. Full-day activities can replace entirely
    placeholder days.

    Returns a list of dicts: [{"day_index": int, "activity": Dict}, ...]
    """
    all_activities = load_activities()
    candidates = filter_by_destination(all_activities, destination)

    # Consider all unused activities — paid ones improve utilization,
    # free ones improve plan quality by replacing placeholders
    available = [
        a for a in candidates
        if a["id"] not in used_ids
    ]
    available.sort(
        key=lambda a: (a["cost"] > 0, score_activity(a, preferences)),
        reverse=True,  # Paid first, then by score
    )

    additions = []
    budget_left = remaining_budget

    for i, day in enumerate(itinerary):
        real_activities = [a for a in day["activities"] if not a.get("is_placeholder", False)]
        real_hours = sum(a["duration_hours"] for a in real_activities)
        real_count = len(real_activities)
        placeholder_count = len(day["activities"]) - real_count

        # Skip days that are already fully packed with real activities
        if real_hours >= MAX_HOURS_PER_DAY or real_count >= MAX_ACTIVITIES_PER_DAY:
            continue

        # Allow full-day activities on days that are entirely placeholders
        if real_count == 0 and placeholder_count > 0:
            full_day_options = [
                a for a in available
                if a["id"] not in used_ids
                and a["time_of_day"] == "full-day"
                and a["cost"] <= budget_left
            ]
            if full_day_options:
                best = max(full_day_options, key=lambda a: score_activity(a, preferences))
                additions.append({"day_index": i, "activity": best, "replace_all_placeholders": True})
                used_ids.add(best["id"])
                budget_left -= best["cost"]
                continue

        # For partially filled days, add activities that fit
        # Use real_hours for capacity check (placeholders will be displaced)
        for activity in available:
            if activity["id"] in used_ids:
                continue
            if activity["cost"] > budget_left:
                continue
            if activity["time_of_day"] == "full-day":
                continue  # Full-day only for empty days (handled above)
            if real_hours + activity["duration_hours"] > MAX_HOURS_PER_DAY:
                continue
            if real_count >= MAX_ACTIVITIES_PER_DAY:
                break

            additions.append({"day_index": i, "activity": activity})
            used_ids.add(activity["id"])
            budget_left -= activity["cost"]
            real_hours += activity["duration_hours"]
            real_count += 1

            if real_count >= MAX_ACTIVITIES_PER_DAY:
                break

        if budget_left <= 0:
            break

    return additions