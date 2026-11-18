import os
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, engine
from .accounts import router as accounts_router
from .security import admin

db.init()
app = FastAPI(title="Smart Sahayak API", version="0.2.0")
DEFAULT_LOC = (24.5362, 81.3037)  # Rewa; used only if the client sends no location


class MatchIn(BaseModel):
    goal: Literal["business", "education"]
    cost: float = Field(gt=0, le=1e9)
    income: float = Field(gt=0, le=1e9)
    years: int = Field(ge=1, le=15)
    category: Literal["sc", "other"]
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class SchemeIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{2,30}$")
    name: str
    goal: Literal["business", "education"]
    min_cost: float = Field(default=0, ge=0)
    max_cost: float | None = None
    support: float = Field(gt=0, le=1)
    loan_cap: float | None = None
    rate_tiers: list[tuple[float, float]] = Field(min_length=1)
    income_cap: float | None = None
    max_years: int = Field(ge=1, le=30)
    docs: list[str]
    source_url: str = ""
    verified: bool = False
    verified_on: str | None = None
    notes: str = ""


class PartnerIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{2,30}$")
    name: str
    type: Literal["PSB", "RRB", "SCA", "MFI"]
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    schemes: list[str]
    last_verified: str
    capacity: float = Field(default=0.5, ge=0, le=1)
    contact: str = ""
    sample: bool = False


class EventIn(BaseModel):
    stage: Literal["recommended", "referred"]
    scheme_id: str | None = Field(default=None, max_length=30)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/schemes")
def schemes():
    return db.list_schemes()


@app.post("/api/match")
def match(u: MatchIn):
    """Stateless: user inputs are evaluated and discarded, never stored."""
    user = {"goal": u.goal, "cost": u.cost, "income": u.income, "years": u.years, "category": u.category}
    sc = db.list_schemes()
    results = sorted((engine.evaluate(s, user) for s in sc), key=lambda r: -r["score"])
    best = results[0] if results and results[0]["ok"] else None
    lat, lng = (u.lat, u.lng) if u.lat is not None and u.lng is not None else DEFAULT_LOC
    partners = engine.route(db.list_partners(), best["id"], lat, lng) if best else []
    return {"results": results, "partners": partners,
            "rules_as_of": max((s["updated_at"] for s in sc), default="")[:10],
            "location_used": "user" if u.lat is not None else "default"}


@app.post("/api/events", status_code=204)
def event(e: EventIn):
    db.log_event(e.stage, e.scheme_id)


@app.put("/api/admin/schemes/{sid}")
def put_scheme(sid: str, s: SchemeIn, who: str = Depends(admin)):
    if sid != s.id:
        raise HTTPException(400, "id in path and body differ")
    return {"id": sid, "version": db.save_scheme(s.model_dump(), who)}


@app.get("/api/admin/schemes/{sid}/history")
def scheme_history(sid: str, _: str = Depends(admin)):
    return db.history_of(sid)


@app.get("/api/admin/partners")
def partners(_: str = Depends(admin)):
    return db.list_partners()


@app.put("/api/admin/partners/{pid}")
def put_partner(pid: str, p: PartnerIn, _: str = Depends(admin)):
    if pid != p.id:
        raise HTTPException(400, "id in path and body differ")
    db.save_partner(p.model_dump())
    return {"id": pid}


@app.get("/api/admin/funnel")
def funnel(_: str = Depends(admin)):
    return db.funnel()


app.include_router(accounts_router, prefix="/api")

FRONT = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONT, html=True), name="web")
