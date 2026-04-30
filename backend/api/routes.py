from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from service.flightsService import get_top_flights
from service.hotelService import get_top_hotels, find_upgrade
from service.activityService import build_itinerary, find_additional_activities
from service.budgetService import calculate_total_cost
from service.validationService import validate_plan

router = APIRouter()

# --- Budget allocation defaults ---
DEFAULT_FLIGHT_PCT = 0.35
MAX_REALLOCATION = 0.20       # Can shift up to 20% from hotel+activity → flights
REALLOCATION_STEP = 0.05      # Each retry bumps flight budget by 5%

# After reallocation, remaining budget is split proportionally:
# Hotel gets ~61.5% of non-flight budget, activities get ~38.5%
HOTEL_SHARE_OF_REMAINING = 0.615
ACTIVITY_SHARE_OF_REMAINING = 0.385

# Budget optimization thresholds
OPTIMIZATION_THRESHOLD = 0.10  # Optimize if >10% budget remains


class TripRequest(BaseModel):
    destination: str = Field(..., example="Tokyo")
    budget: float = Field(..., gt=0, example=1500)
    days: int = Field(..., gt=0, le=30, example=5)
    preferences: List[str] = Field(default=[], example=["food", "tech"])


class TripResponse(BaseModel):
    destination: str
    budget: float
    days: int
    flights: list
    hotels: list
    itinerary: list
    total_cost: float
    breakdown: Dict[str, float]
    within_budget: bool
    warnings: List[str]


@router.post("/plan-trip", response_model=TripResponse)
def plan_trip(request: TripRequest):
    warnings = []

     
    # Phase 1 — Flights (with dynamic budget reallocation)
     
    flight_budget_pct = DEFAULT_FLIGHT_PCT
    flight_result = get_top_flights(
        destination=request.destination,
        budget=request.budget * flight_budget_pct,
    )

    # If no flights found, incrementally increase flight budget
    while (
        not flight_result["flights"]
        and flight_budget_pct < (DEFAULT_FLIGHT_PCT + MAX_REALLOCATION)
    ):
        flight_budget_pct += REALLOCATION_STEP
        flight_result = get_top_flights(
            destination=request.destination,
            budget=request.budget * flight_budget_pct,
        )
        if flight_result["flights"]:
            warnings.append(
                f"Flight budget increased to {flight_budget_pct:.0%} of total "
                f"(${request.budget * flight_budget_pct:.0f}) to find available flights."
            )

    warnings.extend(flight_result["warnings"])

    # Calculate adjusted budget shares for hotel and activity
    remaining_pct = 1.0 - flight_budget_pct
    hotel_budget_pct = remaining_pct * HOTEL_SHARE_OF_REMAINING
    activity_budget_pct = remaining_pct * ACTIVITY_SHARE_OF_REMAINING

    # Phase 2 — Hotels (with adjusted budget)    
    hotel_result = get_top_hotels(
        destination=request.destination,
        total_budget=request.budget,
        days=request.days,
        hotel_budget_pct=hotel_budget_pct,
    )
    warnings.extend(hotel_result["warnings"])

     
    # Phase 3 — Activities (with adjusted budget)
     
    activity_result = build_itinerary(
        destination=request.destination,
        days=request.days,
        preferences=request.preferences,
        total_budget=request.budget,
        activity_budget_pct=activity_budget_pct,
    )
    warnings.extend(activity_result["warnings"])

     
    # Phase 4 — Initial Budget Calculation
     
    selected_flight = flight_result["flights"][0] if flight_result["flights"] else None
    selected_hotel = hotel_result["hotels"][0] if hotel_result["hotels"] else None

    budget_result = calculate_total_cost(
        flight=selected_flight,
        hotel=selected_hotel,
        total_activity_cost=activity_result["total_activity_cost"],
        days=request.days,
        budget=request.budget,
    )
    warnings.extend(budget_result["warnings"])

     
    # Phase 5 — Budget Optimization
     
    remaining = budget_result["breakdown"]["remaining"]
    total_cost = budget_result["total_cost"]

    if remaining > request.budget * OPTIMIZATION_THRESHOLD:
        optimized = False

        # --- Attempt 1: Hotel upgrade ---
        if selected_hotel and remaining > 0:
            # New max per night = (current hotel cost + remaining) / days
            new_max_per_night = (
                selected_hotel["price_per_night"] + (remaining / request.days)
            )
            upgrade = find_upgrade(
                destination=request.destination,
                current_hotel=selected_hotel,
                max_budget_per_night=new_max_per_night,
                days=request.days,
            )
            if upgrade:
                old_cost = selected_hotel["price_per_night"] * request.days
                new_cost = upgrade["price_per_night"] * request.days
                cost_diff = new_cost - old_cost

                if cost_diff <= remaining:
                    # Apply upgrade
                    hotel_result["hotels"][0] = upgrade
                    selected_hotel = upgrade
                    total_cost += cost_diff
                    remaining -= cost_diff
                    optimized = True
                    warnings.append(
                        f"🔼 Upgraded hotel to {upgrade['name']} "
                        f"(rating: {upgrade['rating']}, +${cost_diff:.0f})."
                    )

        # --- Attempt 2: Add activities to underpacked days ---
        if remaining > request.budget * OPTIMIZATION_THRESHOLD:
            # Collect IDs already used
            used_ids = set()
            for day in activity_result["itinerary"]:
                for act in day["activities"]:
                    if not act.get("is_placeholder", False):
                        used_ids.add(act["id"])

            additions = find_additional_activities(
                destination=request.destination,
                used_ids=used_ids,
                remaining_budget=remaining,
                itinerary=activity_result["itinerary"],
                preferences=request.preferences,
            )

            for addition in additions:
                day_idx = addition["day_index"]
                activity = addition["activity"]
                day = activity_result["itinerary"][day_idx]

                if addition.get("replace_all_placeholders"):
                    # Full-day activity replaces the entire day of placeholders
                    removed_hours = sum(
                        a["duration_hours"] for a in day["activities"] if a.get("is_placeholder")
                    )
                    day["activities"] = [
                        a for a in day["activities"] if not a.get("is_placeholder")
                    ]
                    day["day_hours"] = round(day["day_hours"] - removed_hours, 1)
                else:
                    # Replace a single Free Exploration placeholder if one exists
                    placeholder_idx = next(
                        (i for i, a in enumerate(day["activities"]) if a.get("is_placeholder")),
                        None,
                    )
                    if placeholder_idx is not None:
                        replaced = day["activities"].pop(placeholder_idx)
                        day["day_hours"] -= replaced["duration_hours"]

                day["activities"].append(activity)
                day["day_cost"] = round(day["day_cost"] + activity["cost"], 2)
                day["day_hours"] = round(day["day_hours"] + activity["duration_hours"], 1)

                activity_result["total_activity_cost"] = round(
                    activity_result["total_activity_cost"] + activity["cost"], 2
                )
                total_cost += activity["cost"]
                remaining -= activity["cost"]
                optimized = True

            if additions:
                warnings.append(
                    f"🔼 Added {len(additions)} additional activit{'y' if len(additions) == 1 else 'ies'} "
                    f"to improve budget utilization."
                )

        # Recalculate budget after optimization
        if optimized:
            budget_result = calculate_total_cost(
                flight=selected_flight,
                hotel=selected_hotel,
                total_activity_cost=activity_result["total_activity_cost"],
                days=request.days,
                budget=request.budget,
            )
            # Don't re-extend warnings from budget calc — already added

     
    # Phase 6 — Quality Validation
     
    plan_for_validation = {
        "flights": flight_result["flights"],
        "hotels": hotel_result["hotels"],
        "itinerary": activity_result["itinerary"],
        "total_cost": budget_result["total_cost"],
        "budget": request.budget,
    }
    quality_warnings = validate_plan(plan_for_validation)
    warnings.extend(quality_warnings)

    return TripResponse(
        destination=request.destination,
        budget=request.budget,
        days=request.days,
        flights=flight_result["flights"],
        hotels=hotel_result["hotels"],
        itinerary=activity_result["itinerary"],
        total_cost=budget_result["total_cost"],
        breakdown=budget_result["breakdown"],
        within_budget=budget_result["within_budget"],
        warnings=warnings,
    )