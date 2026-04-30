from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from service.flightsService import get_top_flights
from service.hotelService import get_top_hotels
from service.activityService import build_itinerary
from service.budgetService import calculate_total_cost

router = APIRouter()


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

    # Phase 1 — Flights
    # Reserve 35% of budget for flight
    flight_budget = request.budget * 0.35
    flight_result = get_top_flights(
        destination=request.destination,
        budget=flight_budget,
    )
    warnings.extend(flight_result["warnings"])

    # Phase 2 — Hotels
    hotel_result = get_top_hotels(
        destination=request.destination,
        total_budget=request.budget,
        days=request.days,
    )
    warnings.extend(hotel_result["warnings"])

    # Phase 3 — Activities
    activity_result = build_itinerary(
        destination=request.destination,
        days=request.days,
        preferences=request.preferences,
        total_budget=request.budget,
    )
    warnings.extend(activity_result["warnings"])

    # Phase 4 — Budget
    budget_result = calculate_total_cost(
        flight=flight_result["flights"][0] if flight_result["flights"] else None,
        hotel=hotel_result["hotels"][0] if hotel_result["hotels"] else None,
        total_activity_cost=activity_result["total_activity_cost"],
        days=request.days,
        budget=request.budget,
    )
    warnings.extend(budget_result["warnings"])

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