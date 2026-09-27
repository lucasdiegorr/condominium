"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import (
    admin,
    areas,
    auth,
    bookings,
    chart_accounts,
    financial,
    health,
    pets,
    residents,
    units,
    vehicles,
)
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(residents.router)
app.include_router(units.router)
app.include_router(vehicles.router)
app.include_router(pets.router)
app.include_router(areas.router)
app.include_router(bookings.router)
app.include_router(chart_accounts.router)
app.include_router(financial.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
