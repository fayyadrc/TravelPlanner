import json
import os
from typing import List, Dict, Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/hotels.json")

# Scoring weights — adjust in Phase 8 refinement
WEIGHT_RATING = 0.6
WEIGHT_PRICE = 0.4


def load_hotels() -> List[Dict[str, Any]]:
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def compute_max_hotel_budget(total_budget: float, days: int) -> float:
    """
    Allocate 40% of total budget to accommodation.
    Remaining 60% covers flights + activities.
    Returns max spend per night.
    """
    hotel_budget_total = total_budget * 0.40
    return hotel_budget_total / days


def filter_by_destination_and_budget(
    hotels: List[Dict], destination: str, max_per_night: float
) -> List[Dict]:
    """Keep only hotels matching destination and within nightly budget."""
    destination_lower = destination.lower()
    return [
        h for h in hotels
        if h["destination"].lower() == destination_lower
        and h["price_per_night"] <= max_per_night
    ]


def score_hotel(hotel: Dict, candidates: List[Dict]) -> float:
    """
    Score a hotel 0–1 (higher = better).
    Normalises rating (higher = better) and price (lower = better).
    """
    ratings = [h["rating"] for h in candidates]
    prices = [h["price_per_night"] for h in candidates]

    min_rating, max_rating = min(ratings), max(ratings)
    min_price, max_price = min(prices), max(prices)

    rating_score = (
        1.0 if max_rating == min_rating
        else (hotel["rating"] - min_rating) / (max_rating - min_rating)
    )
    price_score = (
        1.0 if max_price == min_price
        else 1 - (hotel["price_per_night"] - min_price) / (max_price - min_price)
    )

    return WEIGHT_RATING * rating_score + WEIGHT_PRICE * price_score


def get_top_hotels(
    destination: str,
    total_budget: float,
    days: int,
    top_n: int = 2,
) -> Dict[str, Any]:
    """
    Return top N hotels for a destination within the hotel budget, ranked by score.

    Returns:
        {
            "hotels": [...],
            "max_per_night": float,
            "warnings": [...]
        }
    """
    warnings = []
    all_hotels = load_hotels()

    max_per_night = compute_max_hotel_budget(total_budget, days)

    # Step 1 — filter
    candidates = filter_by_destination_and_budget(all_hotels, destination, max_per_night)

    if not candidates:
        dest_exists = any(
            h["destination"].lower() == destination.lower() for h in all_hotels
        )
        if not dest_exists:
            warnings.append(f"No hotels found for destination '{destination}'.")
        else:
            warnings.append(
                f"All hotels in '{destination}' exceed the nightly budget of ${max_per_night:.0f}. "
                "Consider increasing total budget or reducing trip length."
            )
        return {"hotels": [], "max_per_night": round(max_per_night, 2), "warnings": warnings}

    # Step 2 — score and sort
    scored = sorted(
        candidates,
        key=lambda h: score_hotel(h, candidates),
        reverse=True,
    )

    top = scored[:top_n]

    # Attach score and total cost for the stay
    for hotel in top:
        hotel["score"] = round(score_hotel(hotel, candidates), 3)
        hotel["total_stay_cost"] = round(hotel["price_per_night"] * days, 2)

    return {
        "hotels": top,
        "max_per_night": round(max_per_night, 2),
        "warnings": warnings,
    }