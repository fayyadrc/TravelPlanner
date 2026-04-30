
from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="AI Travel Planner",
    description="MVP travel planning API — returns realistic itineraries within budget.",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}