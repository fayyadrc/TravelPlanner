import json
import os
from typing import List, Dict, Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/flights.json")

# Scoring weights — adjust in Phase 8 refinement
WEIGHT_PRICE = 0.5
WEIGHT_DURATION = 0.3
WEIGHT_LAYOVERS = 0.2


def load_flights() -> List[Dict[str, Any]]:
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def filter_by_destination_and_budget(flights: List[Dict], destination: str, budget: float) -> List[Dict]:
    """Keep only flights matching destination and within budget."""
    destination_lower = destination.lower()
    return [
        f for f in flights
        if f["destination"].lower() == destination_lower and f["price"] <= budget
    ]


def score_flight(flight: Dict, candidates: List[Dict]) -> float:
    """
    Score a flight 0–1 (higher = better).
    Normalises each factor across the candidate pool so scores are relative.
    """
    prices = [f["price"] for f in candidates]
    durations = [f["duration_hours"] for f in candidates]
    layovers = [f["layovers"] for f in candidates]

    min_price, max_price = min(prices), max(prices)
    min_dur, max_dur = min(durations), max(durations)
    min_lay, max_lay = min(layovers), max(layovers)

    # Normalise: 1.0 = best (cheapest / shortest / fewest stops)
    price_score = (
        1.0 if max_price == min_price
        else 1 - (flight["price"] - min_price) / (max_price - min_price)
    )
    duration_score = (
        1.0 if max_dur == min_dur
        else 1 - (flight["duration_hours"] - min_dur) / (max_dur - min_dur)
    )
    layover_score = (
        1.0 if max_lay == min_lay
        else 1 - (flight["layovers"] - min_lay) / (max_lay - min_lay)
    )

    return (
        WEIGHT_PRICE * price_score
        + WEIGHT_DURATION * duration_score
        + WEIGHT_LAYOVERS * layover_score
    )


def get_top_flights(
    destination: str, budget: float, top_n: int = 3
) -> Dict[str, Any]:
    """
    Return top N flights for a destination within budget, ranked by score.

    Returns:
        {
            "flights": [...],         # ranked list
            "warnings": [...]         # any issues
        }
    """
    warnings = []
    all_flights = load_flights()

    # Step 1 — filter
    candidates = filter_by_destination_and_budget(all_flights, destination, budget)

    if not candidates:
        # Check if destination exists at all
        dest_exists = any(
            f["destination"].lower() == destination.lower() for f in all_flights
        )
        if not dest_exists:
            warnings.append(f"No flights found for destination '{destination}'.")
        else:
            warnings.append(
                f"All flights to '{destination}' exceed the available flight budget of ${budget:.0f}."
            )
        return {"flights": [], "warnings": warnings}

    # Step 2 — score and sort
    scored = sorted(
        candidates,
        key=lambda f: score_flight(f, candidates),
        reverse=True,
    )

    top = scored[:top_n]

    # Attach score to each result for transparency
    for flight in top:
        flight["score"] = round(score_flight(flight, candidates), 3)

    return {"flights": top, "warnings": warnings}