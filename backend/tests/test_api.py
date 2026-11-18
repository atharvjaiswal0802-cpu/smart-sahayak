from datetime import date
from fastapi.testclient import TestClient
from app import engine
from app.main import app

c = TestClient(app)
H = {"X-Admin-Key": "test-key"}
U = dict(goal="business", cost=850000, income=320000, years=5, category="sc")


def test_emi_zero_rate():
    assert round(engine.emi(1200, 0, 1)) == 100


def test_micro_loan_is_capped_at_1_25_lakh():
    s = next(x for x in c.get("/api/schemes").json() if x["id"] == "micro")
    r = engine.evaluate(s, {**U, "cost": 140000})
    assert r["ok"] and r["loan"] == 125000 and r["rate"] == 6.5


def test_term_loan_not_for_tiny_projects_and_non_sc_rejected():
    r = c.post("/api/match", json={**U, "cost": 100000}).json()
    assert not next(x for x in r["results"] if x["id"] == "term")["ok"]
    r = c.post("/api/match", json={**U, "category": "other"}).json()
    assert r["results"][0]["ok"] is False and r["partners"] == []


def test_match_returns_best_and_partners():
    r = c.post("/api/match", json=U).json()
    assert r["results"][0]["id"] == "term" and r["results"][0]["rate"] == 8
    assert r["partners"] and r["partners"][0]["distance_km"] < 20


def test_input_validation():
    assert c.post("/api/match", json={**U, "cost": -5}).status_code == 422


def test_routing_prefers_nearby_fresh():
    P = [dict(id="a", name="A", type="PSB", lat=24.5, lng=81.3, schemes=["term"], last_verified=date.today().isoformat(), capacity=1),
         dict(id="b", name="B", type="PSB", lat=26.5, lng=81.3, schemes=["term"], last_verified="2020-01-01", capacity=1)]
    assert engine.route(P, "term", 24.5, 81.3)[0]["id"] == "a"


def test_admin_requires_key_and_versions_rules():
    assert c.put("/api/admin/schemes/term", json={}).status_code == 401
    s = next(x for x in c.get("/api/schemes").json() if x["id"] == "term")
    body = {k: v for k, v in s.items() if k not in ("version", "updated_at")}
    body["rate_tiers"] = [[5000000, 7.5]]
    r = c.put("/api/admin/schemes/term", json=body, headers=H).json()
    assert r["version"] == s["version"] + 1
    assert len(c.get("/api/admin/schemes/term/history", headers=H).json()) >= 2
    assert c.post("/api/match", json=U).json()["results"][0]["rate"] == 7.5


def test_funnel_events():
    assert c.post("/api/events", json={"stage": "recommended", "scheme_id": "term"}).status_code == 204
    assert c.get("/api/admin/funnel", headers=H).json()["recommended"] >= 1
