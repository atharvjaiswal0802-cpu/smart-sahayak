from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
ADM = {"X-Admin-Key": "test-key"}


def login(phone):
    r = c.post("/api/auth/otp/request", json={"phone": phone})
    assert r.status_code == 202
    v = c.post("/api/auth/otp/verify", json={"phone": phone, "otp": r.json()["dev_otp"]})
    assert v.status_code == 200, v.text
    return v.json(), {"Authorization": "Bearer " + v.json()["token"]}


def test_phone_validation_and_auth_required():
    assert c.post("/api/auth/otp/request", json={"phone": "12345"}).status_code == 422
    assert c.get("/api/me").status_code == 401
    assert c.get("/api/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_wrong_otp_locks_after_five_attempts():
    r = c.post("/api/auth/otp/request", json={"phone": "9000000003"}).json()
    for _ in range(5):
        assert c.post("/api/auth/otp/verify", json={"phone": "9000000003", "otp": "000000" if r["dev_otp"] != "000000" else "111111"}).status_code == 401
    assert c.post("/api/auth/otp/verify", json={"phone": "9000000003", "otp": r["dev_otp"]}).status_code == 401


def test_otp_request_rate_limit_per_phone():
    codes = [c.post("/api/auth/otp/request", json={"phone": "9000000004"}).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]


def test_profile_needs_consent_and_can_be_erased():
    _, H = login("9000000005")
    body = dict(goal="business", cost=500000, income=250000, years=5, category="sc", consent=False)
    assert c.put("/api/me/profile", json=body, headers=H).status_code == 400
    assert c.put("/api/me/profile", json={**body, "consent": True}, headers=H).status_code == 204
    assert c.get("/api/me/profile", headers=H).json()["cost"] == 500000
    assert c.delete("/api/me", headers=H).status_code == 204
    assert c.get("/api/me", headers=H).status_code == 401  # account gone


def test_partner_flow_end_to_end():
    assert c.post("/api/admin/partner-users", json={"partner_id": "p1", "phone": "9000000001"}).status_code == 401
    assert c.post("/api/admin/partner-users", json={"partner_id": "p1", "phone": "9000000001"}, headers=ADM).status_code == 201
    pj, PH = login("9000000001")
    assert pj["role"] == "partner" and pj["partner_id"] == "p1"
    upd = c.put("/api/partner/me", json={"schemes": ["term"], "capacity": 0.9, "contact": "0765-000000"}, headers=PH).json()
    assert upd["schemes"] == ["term"] and upd["capacity"] == 0.9
    assert c.put("/api/partner/me", json={"schemes": ["nope"], "capacity": 0.5}, headers=PH).status_code == 422

    _, CH = login("9000000002")
    assert c.get("/api/partner/me", headers=CH).status_code == 403
    ref = dict(scheme_id="term", partner_id="p1", share_contact=True)
    assert c.post("/api/me/referrals", json=ref, headers=CH).status_code == 400  # no saved details yet
    c.put("/api/me/profile", json=dict(goal="business", cost=850000, income=320000, years=5, category="sc", consent=True), headers=CH)
    assert c.post("/api/me/referrals", json={**ref, "scheme_id": "micro"}, headers=CH).status_code == 400  # p1 now only handles term
    rid = c.post("/api/me/referrals", json=ref, headers=CH).json()["id"]

    rows = c.get("/api/partner/referrals", headers=PH).json()
    mine = next(r for r in rows if r["id"] == rid)
    assert mine["applicant"]["phone"] == "+919000000002" and mine["applicant"]["details"]["cost"] == 850000
    assert c.patch(f"/api/partner/referrals/{rid}", json={"status": "contacted"}, headers=PH).status_code == 200
    assert c.patch(f"/api/partner/referrals/{rid}", json={"status": "contacted"}, headers=PH).status_code == 409
    assert c.get("/api/me/referrals", headers=CH).json()[0]["status"] == "contacted"
    assert c.get("/api/admin/funnel", headers=ADM).json()["referral_contacted"] >= 1


def test_referral_without_sharing_hides_applicant():
    _, CH = login("9000000006")
    rid = c.post("/api/me/referrals", json=dict(scheme_id="term", partner_id="p1"), headers=CH).json()["id"]
    _, PH = login("9000000001")
    assert next(r for r in c.get("/api/partner/referrals", headers=PH).json() if r["id"] == rid)["applicant"] is None
