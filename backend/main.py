import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel_planner")

app = FastAPI(title="Travel Planner MVP")

FLIGHT_ALLOCATION = 0.35
HOTEL_ALLOCATION = 0.40
ACTIVITY_ALLOCATION = 0.25
MAX_REALLOCATION = 0.20
MIN_HOTEL_RATIO = 0.25
MIN_ACTIVITY_RATIO = 0.15
REALLOCATE_HOTEL_SHARE = 0.60
REALLOCATE_ACTIVITY_SHARE = 0.40

MIN_DAY_HOURS = 6.0
MAX_DAY_HOURS = 8.0
FREE_EXPLORATION_HOURS = 2.0
MIN_FREE_EXPLORATION_HOURS = 1.0
AREA_BONUS = 1.5
DISTANCE_PENALTY = 0.5
HOTEL_RATING_WEIGHT = 0.7
HOTEL_STAR_WEIGHT = 0.3
HOTEL_PRICE_WEIGHT_DIVISOR = 200
PREFERENCE_MATCH_WEIGHT = 2.0
ACTIVITY_COST_BASELINE = 2.5
ACTIVITY_COST_DIVISOR = 50
OPTIMIZATION_REMAINING_THRESHOLD = (
    0.1  # Continue adding upgrades while more than 10% of the budget remains.
)
MIN_BUDGET_UTILIZATION = 0.8

ALLOCATION_TOTAL = FLIGHT_ALLOCATION + HOTEL_ALLOCATION + ACTIVITY_ALLOCATION
if abs(ALLOCATION_TOTAL - 1.0) > 0.001:
    raise ValueError("Budget allocation percentages must sum to 1.0.")


FLIGHTS: List[Dict[str, Any]] = [
    {
        "id": "TK-F001",
        "destination": "Tokyo",
        "airline": "JAL",
        "price": 780,
        "duration_hours": 13.5,
        "layovers": 1,
    },
    {
        "id": "TK-F002",
        "destination": "Tokyo",
        "airline": "ANA",
        "price": 820,
        "duration_hours": 12.5,
        "layovers": 1,
    },
    {
        "id": "TK-F003",
        "destination": "Tokyo",
        "airline": "United",
        "price": 650,
        "duration_hours": 15.0,
        "layovers": 2,
    },
    {
        "id": "TK-F004",
        "destination": "Tokyo",
        "airline": "Delta",
        "price": 960,
        "duration_hours": 14.0,
        "layovers": 2,
    },
    {
        "id": "PA-F001",
        "destination": "Paris",
        "airline": "Air France",
        "price": 620,
        "duration_hours": 8.5,
        "layovers": 0,
    },
]

HOTELS: List[Dict[str, Any]] = [
    {
        "id": "TK-H001",
        "destination": "Tokyo",
        "name": "APA Hotel Asakusa",
        "stars": 3,
        "rating": 7.9,
        "price_per_night": 75,
        "area": "Asakusa",
        "amenities": ["wifi", "laundry"],
        "breakfast_included": False,
        "cancellation": "free",
    },
    {
        "id": "TK-H002",
        "destination": "Tokyo",
        "name": "Shinjuku Granbell Hotel",
        "stars": 4,
        "rating": 8.7,
        "price_per_night": 120,
        "area": "Shinjuku",
        "amenities": ["wifi", "gym", "restaurant", "bar"],
        "breakfast_included": False,
        "cancellation": "free",
    },
    {
        "id": "TK-H003",
        "destination": "Tokyo",
        "name": "Mitsui Garden Hotel Ginza",
        "stars": 4,
        "rating": 9.1,
        "price_per_night": 180,
        "area": "Ginza",
        "amenities": ["wifi", "gym", "restaurant"],
        "breakfast_included": True,
        "cancellation": "free",
    },
    {
        "id": "TK-H004",
        "destination": "Tokyo",
        "name": "Park Hyatt Tokyo",
        "stars": 5,
        "rating": 9.4,
        "price_per_night": 240,
        "area": "Shinjuku",
        "amenities": ["wifi", "spa", "pool", "restaurant", "bar"],
        "breakfast_included": True,
        "cancellation": "free",
    },
    {
        "id": "PA-H001",
        "destination": "Paris",
        "name": "Hotel Le Six",
        "stars": 4,
        "rating": 8.8,
        "price_per_night": 190,
        "area": "Montparnasse",
        "amenities": ["wifi", "spa"],
        "breakfast_included": True,
        "cancellation": "free",
    },
]

ACTIVITIES: List[Dict[str, Any]] = [
    {
        "id": "TK-A001",
        "destination": "Tokyo",
        "name": "Tsukiji Outer Market Food Tour",
        "type": ["food"],
        "duration_hours": 2.5,
        "cost": 25,
        "area": "Tsukiji",
        "time_of_day": "morning",
        "description": "Sample fresh sushi, tamagoyaki, and street food at the famous outer market.",
    },
    {
        "id": "TK-A002",
        "destination": "Tokyo",
        "name": "TeamLab Planets Digital Art Museum",
        "type": ["art", "tech"],
        "duration_hours": 2.0,
        "cost": 32,
        "area": "Toyosu",
        "time_of_day": "any",
        "description": "Immersive digital art installations you walk through barefoot.",
    },
    {
        "id": "TK-A003",
        "destination": "Tokyo",
        "name": "Akihabara Tech & Anime Walk",
        "type": ["tech", "shopping"],
        "duration_hours": 3.0,
        "cost": 0,
        "area": "Akihabara",
        "time_of_day": "afternoon",
        "description": "Explore electronics shops, anime stores, and retro game arcades.",
    },
    {
        "id": "TK-A004",
        "destination": "Tokyo",
        "name": "Senso-ji Temple & Asakusa",
        "type": ["culture", "nature"],
        "duration_hours": 2.0,
        "cost": 0,
        "area": "Asakusa",
        "time_of_day": "morning",
        "description": "Tokyo's oldest Buddhist temple with traditional market street Nakamise.",
    },
    {
        "id": "TK-A005",
        "destination": "Tokyo",
        "name": "Ramen Cooking Class",
        "type": ["food"],
        "duration_hours": 3.0,
        "cost": 65,
        "area": "Shinjuku",
        "time_of_day": "afternoon",
        "description": "Learn to make authentic tonkotsu and shoyu ramen from scratch.",
    },
    {
        "id": "TK-A006",
        "destination": "Tokyo",
        "name": "Shibuya Crossing & Harajuku Walk",
        "type": ["culture", "shopping"],
        "duration_hours": 3.0,
        "cost": 0,
        "area": "Shibuya",
        "time_of_day": "afternoon",
        "description": "World's busiest intersection and Japan's street fashion hub.",
    },
    {
        "id": "TK-A007",
        "destination": "Tokyo",
        "name": "Tokyo Skytree Observatory",
        "type": ["sightseeing"],
        "duration_hours": 1.5,
        "cost": 20,
        "area": "Asakusa",
        "time_of_day": "evening",
        "description": "Panoramic views of Tokyo from Japan's tallest tower.",
    },
    {
        "id": "TK-A008",
        "destination": "Tokyo",
        "name": "Ginza Sushi Tasting",
        "type": ["food"],
        "duration_hours": 2.0,
        "cost": 90,
        "area": "Ginza",
        "time_of_day": "evening",
        "description": "Premium omakase tasting with seasonal ingredients.",
    },
    {
        "id": "TK-A009",
        "destination": "Tokyo",
        "name": "Odaiba Seaside Park & Mall",
        "type": ["nature", "shopping"],
        "duration_hours": 2.5,
        "cost": 0,
        "area": "Odaiba",
        "time_of_day": "afternoon",
        "description": "Waterfront stroll with shopping and bay views.",
    },
    {
        "id": "TK-A010",
        "destination": "Tokyo",
        "name": "Ueno Park & Museums",
        "type": ["culture", "art"],
        "duration_hours": 2.5,
        "cost": 15,
        "area": "Ueno",
        "time_of_day": "morning",
        "description": "Visit museums and gardens in Tokyo's cultural hub.",
    },
    {
        "id": "TK-A011",
        "destination": "Tokyo",
        "name": "Robot Entertainment Show",
        "type": ["tech", "entertainment"],
        "duration_hours": 2.0,
        "cost": 85,
        "area": "Shinjuku",
        "time_of_day": "evening",
        "description": "High-energy show with lights, robots, and music.",
    },
    {
        "id": "TK-A012",
        "destination": "Tokyo",
        "name": "Sumida River Cruise",
        "type": ["sightseeing"],
        "duration_hours": 1.5,
        "cost": 30,
        "area": "Asakusa",
        "time_of_day": "afternoon",
        "description": "Relaxing cruise with skyline views.",
    },
    {
        "id": "TK-A013",
        "destination": "Tokyo",
        "name": "Evening Izakaya Crawl",
        "type": ["food"],
        "duration_hours": 2.0,
        "cost": 55,
        "area": "Shinjuku",
        "time_of_day": "evening",
        "description": "Sample local bites and drinks in cozy izakayas.",
    },
    {
        "id": "TK-A014",
        "destination": "Tokyo",
        "name": "Ghibli Museum Visit",
        "type": ["art", "culture"],
        "duration_hours": 2.0,
        "cost": 30,
        "area": "Mitaka",
        "time_of_day": "morning",
        "description": "Explore the whimsical world of Studio Ghibli.",
    },
    {
        "id": "PA-A001",
        "destination": "Paris",
        "name": "Louvre Highlights Tour",
        "type": ["art", "culture"],
        "duration_hours": 3.0,
        "cost": 45,
        "area": "Louvre",
        "time_of_day": "morning",
        "description": "Guided tour of the Louvre's masterpieces.",
    },
]


class PlanRequest(BaseModel):
    destination: str
    budget: float = Field(gt=0)
    days: int = Field(gt=0)
    preferences: List[str] = Field(default_factory=list)


def normalize_destination(destination: str) -> str:
    return destination.strip().lower()


def allocate_budget(total_budget: float) -> Dict[str, float]:
    return {
        "flight": total_budget * FLIGHT_ALLOCATION,
        "hotel": total_budget * HOTEL_ALLOCATION,
        "activities": total_budget * ACTIVITY_ALLOCATION,
    }


def min_flight_cost(destination: str) -> Optional[float]:
    normalized = normalize_destination(destination)
    costs = [
        flight["price"]
        for flight in FLIGHTS
        if normalize_destination(flight["destination"]) == normalized
    ]
    return float(min(costs)) if costs else None


def min_hotel_cost(hotel_candidates: List[Dict[str, Any]]) -> Optional[float]:
    costs = [hotel["total_stay_cost"] for hotel in hotel_candidates]
    return float(min(costs)) if costs else None


def select_flights(destination: str, flight_budget: float) -> List[Dict[str, Any]]:
    normalized = normalize_destination(destination)
    candidates = [
        flight
        for flight in FLIGHTS
        if normalize_destination(flight["destination"]) == normalized
        and flight["price"] <= flight_budget
    ]
    ranked = sorted(
        candidates,
        key=lambda flight: (flight["price"], flight["duration_hours"], flight["layovers"]),
    )
    return ranked[:3]


def reallocate_for_flights(
    budgets: Dict[str, float], total_budget: float
) -> Tuple[Dict[str, float], float]:
    max_shift = total_budget * MAX_REALLOCATION
    min_hotel = total_budget * MIN_HOTEL_RATIO
    min_activities = total_budget * MIN_ACTIVITY_RATIO

    shift_hotel = min(
        max_shift * REALLOCATE_HOTEL_SHARE, max(0.0, budgets["hotel"] - min_hotel)
    )
    shift_activities = min(
        max_shift * REALLOCATE_ACTIVITY_SHARE,
        max(0.0, budgets["activities"] - min_activities),
    )
    total_shift = shift_hotel + shift_activities
    if total_shift <= 0:
        return budgets, 0.0

    reallocated = {
        "flight": budgets["flight"] + total_shift,
        "hotel": budgets["hotel"] - shift_hotel,
        "activities": budgets["activities"] - shift_activities,
    }
    logger.info(
        "Reallocating budget for flights: shift=%.2f flight=%.2f hotel=%.2f activities=%.2f",
        total_shift,
        reallocated["flight"],
        reallocated["hotel"],
        reallocated["activities"],
    )
    return reallocated, total_shift


def hotel_score(hotel: Dict[str, Any]) -> float:
    return (
        hotel["rating"] * HOTEL_RATING_WEIGHT
        + hotel["stars"] * HOTEL_STAR_WEIGHT
        - hotel["price_per_night"] / HOTEL_PRICE_WEIGHT_DIVISOR
    )


def select_hotels(
    destination: str, hotel_budget: float, days: int
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    normalized = normalize_destination(destination)
    candidates = []
    for hotel in HOTELS:
        if normalize_destination(hotel["destination"]) != normalized:
            continue
        total_cost = hotel["price_per_night"] * days
        enriched = {**hotel, "total_stay_cost": total_cost, "score": hotel_score(hotel)}
        candidates.append(enriched)

    within_budget = [hotel for hotel in candidates if hotel["total_stay_cost"] <= hotel_budget]
    if not within_budget and candidates:
        logger.info("No hotels within budget %.2f, selecting cheapest option.", hotel_budget)
        within_budget = sorted(candidates, key=lambda hotel: hotel["total_stay_cost"])[:1]

    ranked = sorted(within_budget, key=lambda hotel: (-hotel["score"], hotel["total_stay_cost"]))
    selected = ranked[0] if ranked else None
    return ranked[:2], selected, candidates


def preference_score(activity: Dict[str, Any], preferences: List[str]) -> float:
    if not preferences:
        return 0.0
    matches = set(preferences) & set(activity["type"])
    return float(len(matches)) * PREFERENCE_MATCH_WEIGHT


def activity_score(
    activity: Dict[str, Any], preferences: List[str], day_area: Optional[str]
) -> float:
    score = preference_score(activity, preferences)
    score += max(0.0, ACTIVITY_COST_BASELINE - activity["cost"] / ACTIVITY_COST_DIVISOR)
    if day_area:
        if activity["area"] == day_area:
            score += AREA_BONUS
        else:
            score -= DISTANCE_PENALTY
    return score


def pick_activity(
    activities: List[Dict[str, Any]],
    used_ids: set,
    preferences: List[str],
    day_area: Optional[str],
    remaining_budget: float,
    remaining_hours: float,
    prefer_expensive_activities: bool = False,
) -> Optional[Dict[str, Any]]:
    candidates = []
    for activity in activities:
        if activity["id"] in used_ids:
            continue
        if activity["cost"] > remaining_budget:
            continue
        if activity["duration_hours"] > remaining_hours:
            continue
        candidates.append(activity)

    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda activity: (
            -activity_score(activity, preferences, day_area),
            -activity["cost"] if prefer_expensive_activities else activity["cost"],
        ),
    )
    return ranked[0]


def add_free_exploration(day: int, exploration_index: int, duration: float) -> Dict[str, Any]:
    return {
        "id": f"FREE-{day}-{exploration_index}",
        "destination": "",
        "name": "Free Exploration",
        "type": ["flex"],
        "duration_hours": duration,
        "cost": 0,
        "area": "flex",
        "time_of_day": "any",
        "description": "Open time to wander, rest, or explore locally.",
    }


def plan_itinerary(
    destination: str,
    days: int,
    preferences: List[str],
    activity_budget: float,
) -> Tuple[List[Dict[str, Any]], float, set]:
    normalized = normalize_destination(destination)
    activities = [
        activity
        for activity in ACTIVITIES
        if normalize_destination(activity["destination"]) == normalized
    ]
    used_ids: set = set()
    remaining_budget = activity_budget
    itinerary = []

    for day in range(1, days + 1):
        day_activities: List[Dict[str, Any]] = []
        day_hours = 0.0
        day_cost = 0.0
        day_area: Optional[str] = None
        free_index = 1

        while day_hours < MIN_DAY_HOURS:
            remaining_hours = MAX_DAY_HOURS - day_hours
            if remaining_hours <= 0:
                break

            candidate = pick_activity(
                activities,
                used_ids,
                preferences,
                day_area,
                remaining_budget,
                remaining_hours,
            )
            if not candidate:
                break

            used_ids.add(candidate["id"])
            day_activities.append(candidate)
            day_hours += candidate["duration_hours"]
            day_cost += candidate["cost"]
            remaining_budget -= candidate["cost"]
            day_area = day_area or candidate["area"]

        if day_hours < MIN_DAY_HOURS:
            while day_hours < MIN_DAY_HOURS and day_hours < MAX_DAY_HOURS:
                remaining_hours = MAX_DAY_HOURS - day_hours
                needed = MIN_DAY_HOURS - day_hours
                duration = min(
                    max(needed, MIN_FREE_EXPLORATION_HOURS),
                    remaining_hours,
                    FREE_EXPLORATION_HOURS,
                )
                day_activities.append(add_free_exploration(day, free_index, duration))
                free_index += 1
                day_hours += duration

        if day_hours < MIN_DAY_HOURS:
            logger.info(
                "Day %s under minimum hours (%.1f) after planning.", day, day_hours
            )

        itinerary.append(
            {
                "day": day,
                "activities": day_activities,
                "day_cost": round(day_cost, 2),
                "day_hours": round(day_hours, 1),
            }
        )

    return itinerary, activity_budget - remaining_budget, used_ids


def upgrade_hotel(
    current: Dict[str, Any],
    options: List[Dict[str, Any]],
    total_budget: float,
    total_cost: float,
) -> Tuple[Dict[str, Any], float, bool]:
    best = current
    new_total = total_cost
    for hotel in sorted(options, key=lambda hotel: (-hotel["score"], hotel["total_stay_cost"])):
        if hotel["total_stay_cost"] <= current["total_stay_cost"]:
            continue
        candidate_total = total_cost - current["total_stay_cost"] + hotel["total_stay_cost"]
        if candidate_total <= total_budget:
            best = hotel
            new_total = candidate_total
            break
    return best, new_total, best["id"] != current["id"]


def add_optional_activity(
    itinerary: List[Dict[str, Any]],
    activities: List[Dict[str, Any]],
    used_ids: set,
    preferences: List[str],
    remaining_budget: float,
) -> Tuple[float, bool]:
    for day in itinerary:
        remaining_hours = MAX_DAY_HOURS - day["day_hours"]
        if remaining_hours <= 0:
            continue
        day_area = None
        if day["activities"]:
            day_area = day["activities"][-1]["area"]
        candidate = pick_activity(
            activities,
            used_ids,
            preferences,
            day_area,
            remaining_budget,
            remaining_hours,
            prefer_expensive_activities=True,
        )
        if not candidate:
            continue
        used_ids.add(candidate["id"])
        day["activities"].append(candidate)
        day["day_hours"] = round(day["day_hours"] + candidate["duration_hours"], 1)
        day["day_cost"] = round(day["day_cost"] + candidate["cost"], 2)
        return candidate["cost"], True
    return 0.0, False


def optimize_plan(
    plan: Dict[str, Any],
    total_budget: float,
    hotel_candidates: List[Dict[str, Any]],
    selected_hotel: Optional[Dict[str, Any]],
    itinerary: List[Dict[str, Any]],
    activities: List[Dict[str, Any]],
    used_ids: set,
    preferences: List[str],
) -> Tuple[Dict[str, Any], float]:
    total_cost = plan["total_cost"]
    remaining_budget = total_budget - total_cost

    if selected_hotel and hotel_candidates:
        upgraded, new_total, changed = upgrade_hotel(
            selected_hotel, hotel_candidates, total_budget, total_cost
        )
        if changed:
            logger.info("Upgraded hotel to %s", upgraded["name"])
            plan["hotels"][0] = upgraded
            selected_hotel = upgraded
            total_cost = new_total
            remaining_budget = total_budget - total_cost
            plan["breakdown"]["hotel"] = upgraded["total_stay_cost"]

    improvement = True
    while remaining_budget > total_budget * OPTIMIZATION_REMAINING_THRESHOLD and improvement:
        improvement = False
        spent, added = add_optional_activity(
            itinerary, activities, used_ids, preferences, remaining_budget
        )
        if added:
            total_cost += spent
            remaining_budget = total_budget - total_cost
            plan["breakdown"]["activities"] += spent
            improvement = True

    plan["total_cost"] = round(total_cost, 2)
    plan["breakdown"]["remaining"] = round(remaining_budget, 2)
    return plan, remaining_budget


def get_plan_warnings(
    plan: Dict[str, Any], total_budget: float
) -> List[str]:
    warnings: List[str] = []

    if not plan["flights"]:
        warnings.append("No flights selected")
    if not plan["hotels"]:
        warnings.append("No hotels selected")

    seen_ids = set()
    duplicates = set()
    for day in plan["itinerary"]:
        for activity in day["activities"]:
            activity_id = activity["id"]
            if activity_id.startswith("FREE-"):
                continue
            if activity_id in seen_ids:
                duplicates.add(activity_id)
            seen_ids.add(activity_id)

    if duplicates:
        warnings.append("Duplicate activities detected")

    if plan["total_cost"] / total_budget < MIN_BUDGET_UTILIZATION:
        warnings.append("Low budget utilization")

    for day in plan["itinerary"]:
        if day["day_hours"] < MIN_DAY_HOURS:
            warnings.append(
                f"Day {day['day']}: fewer than minimum recommended hours of activities"
            )
        if day["day_hours"] > MAX_DAY_HOURS:
            warnings.append(
                f"Day {day['day']}: exceeds maximum recommended hours of activities"
            )

    return warnings


def build_plan(request: PlanRequest) -> Dict[str, Any]:
    budgets = allocate_budget(request.budget)
    flights = select_flights(request.destination, budgets["flight"])
    warnings: List[str] = []
    if not flights:
        reallocated_budgets, shift_amount = reallocate_for_flights(
            budgets, request.budget
        )
        if shift_amount > 0:
            budgets = reallocated_budgets
            warnings.append(
                f"Reallocated ${shift_amount:.0f} toward flights to find options within budget."
            )
        flights = select_flights(request.destination, budgets["flight"])
        if not flights:
            warnings.append(
                f"All flights to '{request.destination}' exceed the available flight budget of "
                f"${budgets['flight']:.0f}."
            )

    hotel_options, selected_hotel, hotel_candidates = select_hotels(
        request.destination, budgets["hotel"], request.days
    )

    itinerary, activity_spend, used_ids = plan_itinerary(
        request.destination, request.days, request.preferences, budgets["activities"]
    )

    missing_costs = False
    if flights:
        flight_cost = min(flight["price"] for flight in flights)
    else:
        flight_cost = min_flight_cost(request.destination)
        if flight_cost is None:
            missing_costs = True
            flight_cost = 0.0
            warnings.append(f"No flight data available for '{request.destination}'.")
        else:
            warnings.append(
                f"Estimated minimum flight cost is ${flight_cost:.0f} based on available data."
            )

    hotel_cost = (
        selected_hotel["total_stay_cost"]
        if selected_hotel
        else min_hotel_cost(hotel_candidates)
    )
    if not selected_hotel:
        if hotel_cost is None:
            missing_costs = True
            hotel_cost = 0.0
            warnings.append(
                f"No hotel data available for '{request.destination}'."
            )
        else:
            warnings.append(
                "No hotel matched the current budget; using minimum available stay cost for estimates."
            )
    total_cost = flight_cost + hotel_cost + activity_spend

    plan = {
        "destination": request.destination,
        "budget": round(request.budget, 2),
        "days": request.days,
        "flights": flights,
        "hotels": hotel_options,
        "itinerary": itinerary,
        "total_cost": round(total_cost, 2),
        "breakdown": {
            "flight": round(flight_cost, 2),
            "hotel": round(hotel_cost, 2),
            "activities": round(activity_spend, 2),
            "remaining": round(request.budget - total_cost, 2),
        },
        "within_budget": total_cost <= request.budget and not missing_costs,
        "warnings": warnings,
    }

    normalized = normalize_destination(request.destination)
    activities = [
        activity
        for activity in ACTIVITIES
        if normalize_destination(activity["destination"]) == normalized
    ]

    plan, _ = optimize_plan(
        plan,
        request.budget,
        hotel_candidates,
        selected_hotel,
        itinerary,
        activities,
        used_ids,
        request.preferences,
    )

    plan["within_budget"] = plan["total_cost"] <= request.budget and not missing_costs
    plan["warnings"].extend(get_plan_warnings(plan, request.budget))
    return plan


@app.post("/plan-trip")
async def plan_trip(request: PlanRequest) -> Dict[str, Any]:
    return build_plan(request)
