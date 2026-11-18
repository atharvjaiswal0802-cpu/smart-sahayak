"""OTP login, citizen profile + referrals, partner self-service."""
import hmac, json, os
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import db
from .security import (admin, current_user, dec, enc, hash_otp, hash_phone, is_prod, limiter, make_token,
                       new_otp, normalize_phone, send_sms)

router = APIRouter()
CONSENT_VERSION = "v1"
FLOW = ["referred", "contacted", "documents_requested", "applied", "approved", "disbursed"]


class PhoneIn(BaseModel):
    phone: str = Field(max_length=20)


class VerifyIn(PhoneIn):
    otp: str = Field(pattern=r"^\d{6}$")


class ProfileIn(BaseModel):
    goal: Literal["business", "education"]
    cost: float = Field(gt=0, le=1e9)
    income: float = Field(gt=0, le=1e9)
    years: int = Field(ge=1, le=15)
    category: Literal["sc", "other"]
    consent: bool


class ReferralIn(BaseModel):
    scheme_id: str
    partner_id: str
    share_contact: bool = False


class PartnerSelfIn(BaseModel):
    schemes: list[str]
    capacity: float = Field(ge=0, le=1)
    contact: str = Field(default="", max_length=200)


class StatusIn(BaseModel):
    status: Literal["contacted", "documents_requested", "applied", "approved", "rejected", "disbursed"]


class PartnerUserIn(PhoneIn):
    partner_id: str


def partner_user(u: dict = Depends(current_user)) -> dict:
    if u["role"] != "partner" or not u["partner_id"]:
        raise HTTPException(403, "Partner account required")
    return u


# ---------- OTP login ----------
@router.post("/auth/otp/request", status_code=202)
def otp_request(b: PhoneIn, req: Request):
    limiter.hit("ip:" + (req.client.host if req.client else "?"), 20, 600)
    phone = normalize_phone(b.phone)
    h = hash_phone(phone)
    if db.otp_count_since(h, db.now(-600)) >= 3:
        raise HTTPException(429, "Too many OTP requests for this number. Try again in a few minutes.")
    code = new_otp()
    db.otp_add(h, hash_otp(h, code), db.now(300))
    send_sms(phone, f"Your Smart Sahayak OTP is {code}. Valid for 5 minutes. Do not share it with anyone.")
    out = {"sent": True}
    if os.getenv("OTP_DEV_ECHO") == "1" and not is_prod():
        out["dev_otp"] = code  # development only; never enabled in production
    return out


@router.post("/auth/otp/verify")
def otp_verify(b: VerifyIn):
    phone = normalize_phone(b.phone)
    h = hash_phone(phone)
    o = db.otp_latest(h)
    if not o or o["expires_at"] < db.now() or o["attempts"] >= 5:
        raise HTTPException(401, "OTP expired or locked. Request a new one.")
    db.otp_attempt(o["id"])
    if not hmac.compare_digest(o["code_hash"], hash_otp(h, b.otp)):
        raise HTTPException(401, "Incorrect OTP")
    db.otp_clear(h)
    pid = db.partner_for_hash(h)
    u = db.upsert_user(h, enc(phone), "partner" if pid else "citizen", pid)
    return {"token": make_token(u), "role": u["role"], "partner_id": pid}


# ---------- citizen ----------
@router.get("/me")
def me(u: dict = Depends(current_user)):
    return {"id": u["id"], "role": u["role"], "partner_id": u["partner_id"]}


@router.put("/me/profile", status_code=204)
def put_profile(p: ProfileIn, u: dict = Depends(current_user)):
    if not p.consent:
        raise HTTPException(400, "Consent is required to save your details")
    db.profile_set(u["id"], enc(p.model_dump_json(exclude={"consent"})), CONSENT_VERSION)


@router.get("/me/profile")
def get_profile(u: dict = Depends(current_user)):
    r = db.profile_get(u["id"])
    if not r:
        raise HTTPException(404, "No saved details")
    return json.loads(dec(r["data_enc"]))


@router.delete("/me", status_code=204)
def delete_me(u: dict = Depends(current_user)):
    db.delete_user(u["id"])


@router.post("/me/referrals", status_code=201)
def refer(b: ReferralIn, u: dict = Depends(current_user)):
    if not any(s["id"] == b.scheme_id for s in db.list_schemes()):
        raise HTTPException(404, "Unknown scheme")
    p = next((x for x in db.list_partners() if x["id"] == b.partner_id), None)
    if not p or b.scheme_id not in p["schemes"]:
        raise HTTPException(400, "This partner does not currently handle that scheme")
    snap = ""
    if b.share_contact:
        prof = db.profile_get(u["id"])
        if not prof:
            raise HTTPException(400, "Save your details first to share them with the branch")
        snap = enc(json.dumps({"phone": dec(u["phone_enc"]), "details": json.loads(dec(prof["data_enc"]))}))
    return {"id": db.referral_add(u["id"], b.partner_id, b.scheme_id, b.share_contact, snap)}


@router.get("/me/referrals")
def my_referrals(u: dict = Depends(current_user)):
    return [{k: r[k] for k in ("id", "partner_id", "scheme_id", "status", "created_at", "updated_at")} | {"shared": r["share_contact"]}
            for r in db.referrals_for_user(u["id"])]


# ---------- partner self-service ----------
@router.get("/partner/me")
def partner_me(u: dict = Depends(partner_user)):
    p = next((x for x in db.list_partners() if x["id"] == u["partner_id"]), None)
    if not p:
        raise HTTPException(404, "Partner record missing")
    return p


@router.put("/partner/me")
def partner_update(b: PartnerSelfIn, u: dict = Depends(partner_user)):
    """Partners confirm what they handle and fund capacity. This also resets the data-freshness clock."""
    known = {s["id"] for s in db.list_schemes()}
    if not set(b.schemes) <= known:
        raise HTTPException(422, "Unknown scheme id")
    p = partner_me(u) | {"schemes": b.schemes, "capacity": b.capacity, "contact": b.contact, "last_verified": date.today().isoformat()}
    db.save_partner(p)
    return p


@router.get("/partner/referrals")
def partner_referrals(u: dict = Depends(partner_user)):
    out = []
    for r in db.referrals_for_partner(u["partner_id"]):
        snap = json.loads(dec(r["snapshot_enc"])) if r["share_contact"] and r["snapshot_enc"] else None
        out.append({"id": r["id"], "scheme_id": r["scheme_id"], "status": r["status"], "created_at": r["created_at"], "applicant": snap})
    return out


@router.patch("/partner/referrals/{rid}")
def partner_set_status(rid: str, b: StatusIn, u: dict = Depends(partner_user)):
    r = db.referral_get(rid)
    if not r or r["partner_id"] != u["partner_id"]:
        raise HTTPException(404, "Referral not found")
    cur = r["status"]
    if cur in ("approved", "disbursed", "rejected") and not (cur == "approved" and b.status == "disbursed"):
        raise HTTPException(409, f"Referral is already {cur}")
    if b.status != "rejected" and FLOW.index(b.status) <= FLOW.index(cur):
        raise HTTPException(409, "Status can only move forward")
    db.referral_status(rid, b.status)
    return {"id": rid, "status": b.status}


# ---------- admin: link a phone number to a partner branch ----------
@router.post("/admin/partner-users", status_code=201)
def link_partner_user(b: PartnerUserIn, _: str = Depends(admin)):
    if not any(p["id"] == b.partner_id for p in db.list_partners()):
        raise HTTPException(404, "Unknown partner")
    db.link_partner_user(hash_phone(normalize_phone(b.phone)), b.partner_id)
    return {"linked": b.partner_id}
