# AI Multi-Agent Travel Planner — MVP PRD (Execution-Focused)

## 1. Product Overview
This project is a **working travel planning system** that generates usable itineraries based on real constraints (budget, duration, preferences).

The goal is not to showcase AI — it is to build a system people can actually use.

AI is only used where it adds value. Core decisions are deterministic.

---

## 2. Core MVP Goal

Build a system that:
- Takes structured travel input
- Produces a realistic, usable itinerary
- Stays within budget
- Avoids logical inconsistencies

If a user can realistically follow the trip plan → MVP success.

---

## 3. Non-Goals (Important)

This MVP will NOT:
- Use multiple complex LLM chains everywhere
- Depend on external APIs initially
- Attempt perfect personalization

Focus: **working > impressive**

---

## 4. Core Features (Strict MVP Scope)

### Input
- Destination
- Budget
- Number of days
- Preferences (simple tags)

### Output
- Flights (top 2–3 options)
- Hotel (1–2 solid options)
- Day-by-day itinerary
- Total estimated cost
- Warnings if constraints fail

---

## 5. System Design (Simplified)

Instead of many agents, MVP uses **4 core modules**:

1. Flight Selector
2. Hotel Selector
3. Activity Planner
4. Budget + Constraint Validator

Optional later:
- Orchestrator abstraction
- Additional agents

---

## 6. Execution Flow

1. Receive request
2. Fetch + score flights
3. Fetch + score hotels
4. Generate activities per day
5. Calculate total cost
6. Validate constraints
7. Return final plan

No unnecessary parallelism initially — correctness first.

---

## 7. Data Strategy (Critical)

### Phase 1 (MVP)
Use **clean mock datasets**:
- flights.json
- hotels.json
- activities.json

Requirements:
- Realistic pricing ranges
- Enough variety for meaningful selection

Bad data = bad product

---

## 8. Logic Design

### Flight Selection
- Filter by budget
- Rank by:
  - price
  - duration
  - layovers

### Hotel Selection
- Price per night within budget
- Rank by:
  - rating
  - price

### Activity Planning
- Match activities to preferences
- Distribute across days evenly
- Avoid overloading days

### Budget Calculation
- flight + (hotel * days) + estimated daily spend

### Constraint Validation
- Total cost <= budget
- Reasonable number of activities per day

---

## 9. API Design

### POST /plan-trip

#### Input
```
{
  "destination": "Tokyo",
  "budget": 1500,
  "days": 5,
  "preferences": ["food", "tech"]
}
```

#### Output
```
{
  "destination": "Tokyo",
  "total_cost": 1320,
  "flights": [],
  "hotel": {},
  "itinerary": [],
  "warnings": []
}
```

---

## 10. Tech Stack (MVP)

Backend:
- FastAPI
- Python (async optional, not required initially)

Database:
- None required for MVP (optional logging later)

Frontend:
- Optional (Postman is enough initially)

---

## 11. Development Plan (Realistic)

### Day 1–2
- FastAPI setup
- Mock datasets

### Day 3–4
- Flight + Hotel logic

### Day 5–6
- Activity planner

### Day 7
- Budget + validation

### Day 8
- Final response formatting

---

## 12. Definition of Done

MVP is complete when:
- API returns a full itinerary
- Output is logically consistent
- Budget is respected
- No crashes on normal input

---

## 13. Future Enhancements (After MVP Works)

Only after MVP is stable:
- WebSocket streaming
- Supabase storage
- Real APIs (Amadeus, Google Places)
- Smarter AI summarization

---

## Final Principle

A simple system that works is more valuable than a complex system that looks impressive.

Build something usable first. Then scale.
