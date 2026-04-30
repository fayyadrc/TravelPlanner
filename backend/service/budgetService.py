from typing import Dict, Any, Optional


def calculate_total_cost(
    flight: Optional[Dict[str, Any]],
    hotel: Optional[Dict[str, Any]],
    total_activity_cost: float,
    days: int,
    budget: float,
) -> Dict[str, Any]:

    """
    Calculate the real total cost of the recommended trip.

    Inputs:
    - flight: Top-ranked flight dict (or None if no flight available)
    - hotel: Top-ranked hotel dict (or None if no hotel available)
    - total_activity_cost: Sum of all activity costs for the trip
    - days: Number of days in the trip
    - budget: Total trip budget

    Returns:
        {
            "total_cost": float,
            "breakdown": {
                "flight": float,
                "hotel": float,
                "activities": float,
                "remaining": float  # budget - total_cost (can be negative)
            },
            "within_budget": bool,
            "warnings": List[str]
        }
    """
    warnings = []

    # Phase 4 — Cost Calculation
    flight_cost = 0.0
    if flight:
        flight_cost = flight["price"]
    else:
        warnings.append("No flight selected — flight cost excluded from total.")

    hotel_cost = 0.0
    if hotel:
        hotel_cost = hotel["price_per_night"] * days
    else:
        warnings.append("No hotel selected — accommodation cost excluded from total.")

    activity_cost = total_activity_cost

    # Total cost sum
    total_cost = flight_cost + hotel_cost + activity_cost

    # Remaining budget (can be negative)
    remaining = budget - total_cost

    # Breakdown
    breakdown = {
        "flight": round(flight_cost, 2),
        "hotel": round(hotel_cost, 2),
        "activities": round(activity_cost, 2),
        "remaining": round(remaining, 2),
    }

    # Within budget check
    within_budget = total_cost <= budget

    return {
        "total_cost": round(total_cost, 2),
        "breakdown": breakdown,
        "within_budget": within_budget,
        "warnings": warnings,
    }
