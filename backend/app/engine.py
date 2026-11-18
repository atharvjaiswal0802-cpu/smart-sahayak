"""Deterministic, explainable eligibility + routing engine (no ML in the decision path)."""
from datetime import date
from math import asin, cos, radians, sin, sqrt


def emi(principal: float, annual_rate: float, years: float) -> float:
    i, n = annual_rate / 1200, round(years * 12)
    if n <= 0:
        return principal
    return principal / n if i == 0 else principal * i * (1 + i) ** n / ((1 + i) ** n - 1)


def haversine(lat1, lng1, lat2, lng2) -> float:
    d = radians
    a = sin(d(lat2 - lat1) / 2) ** 2 + cos(d(lat1)) * cos(d(lat2)) * sin(d(lng2 - lng1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def rate_for(scheme: dict, loan: float) -> float:
    for upto, rate in scheme["rate_tiers"]:
        if loan <= upto:
            return rate
    return scheme["rate_tiers"][-1][1]


def inr(n: float) -> str:
    return f"Rs {round(n):,}"


def evaluate(s: dict, u: dict) -> dict:
    why, ok = [], True
    if u["category"] != "sc":
        ok = False
        why.append("These schemes are for Scheduled Caste beneficiaries")
    if s["goal"] != u["goal"]:
        ok = False
        why.append(f"Scheme is for {s['goal']} purposes")
    if s.get("income_cap") and u["income"] > s["income_cap"]:
        ok = False
        why.append(f"Income above the {inr(s['income_cap'])} limit")
    if u["cost"] < s["min_cost"]:
        ok = False
        why.append(f"Cost is below the {inr(s['min_cost'])} minimum for this scheme")
    if s.get("max_cost") and u["cost"] > s["max_cost"]:
        ok = False
        why.append(f"Cost is above the {inr(s['max_cost'])} ceiling")
    years = min(u["years"], s["max_years"])
    loan = u["cost"] * s["support"]
    if s.get("loan_cap"):
        loan = min(loan, s["loan_cap"])
    rate = rate_for(s, loan)
    m = emi(loan, rate, years)
    ratio = m * 12 / u["income"]
    if ok:
        why.append(f"Funds up to {round(s['support'] * 100)}% of cost; loan capped at {inr(s['loan_cap'])}" if s.get("loan_cap")
                   else f"Funds up to {round(s['support'] * 100)}% of cost")
        why.append(f"EMI is {round(ratio * 100)}% of your monthly income")
        if u["years"] > s["max_years"]:
            why.append(f"Repayment capped at {s['max_years']} years")
    score = 100 - rate * 3 + s["support"] * 20 - min(ratio, 1) * 30 if ok else 0
    return {"id": s["id"], "name": s["name"], "ok": ok, "why": why, "loan": loan, "emi": m, "years": years,
            "rate": rate, "ratio": ratio, "own": u["cost"] - loan, "total": m * years * 12 - loan,
            "docs": s["docs"], "verify": not s.get("verified", False), "score": score}


def route(partners: list, scheme_id: str, lat: float, lng: float, today: date | None = None, limit: int = 4) -> list:
    """Score = 40 scheme coverage + 25 proximity + 15 data freshness + 20 fund capacity."""
    today, out = today or date.today(), []
    for p in partners:
        if scheme_id not in p["schemes"]:
            continue
        dist = haversine(lat, lng, p["lat"], p["lng"])
        age = (today - date.fromisoformat(p["last_verified"])).days
        score = 40 + 25 * max(0, 1 - dist / 100) + 15 * max(0, 1 - age / 30) + 20 * p.get("capacity", 0.5)
        out.append({"id": p["id"], "name": p["name"], "type": p["type"], "distance_km": round(dist, 1),
                    "age_days": age, "score": round(score), "sample": p.get("sample", False),
                    "contact": p.get("contact", "")})
    return sorted(out, key=lambda x: -x["score"])[:limit]
