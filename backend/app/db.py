"""Storage layer (SQLAlchemy Core). PostgreSQL via DATABASE_URL; SQLite file fallback for local dev."""
import json, os
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import (Boolean, Column, Integer, MetaData, String, Table, Text, create_engine, delete, func,
                        insert, select, update)


def _url() -> str:
    u = os.getenv("DATABASE_URL")
    if u:
        if u.startswith("postgres://"):
            u = "postgresql://" + u[11:]
        if u.startswith("postgresql://"):
            u = "postgresql+psycopg://" + u[13:]
        return u
    return "sqlite:///" + os.getenv("SAHAYAK_DB", str(Path(__file__).resolve().parents[1] / "sahayak.db"))


engine = create_engine(_url(), pool_pre_ping=True)
md = MetaData()
T = lambda name, *cols: Table(name, md, *cols)
schemes = T("schemes", Column("id", String(40), primary_key=True), Column("data", Text), Column("version", Integer), Column("updated_at", String(40)))
history = T("scheme_history", Column("pk", Integer, primary_key=True, autoincrement=True), Column("id", String(40), index=True), Column("version", Integer), Column("data", Text), Column("updated_at", String(40)), Column("editor", String(80)))
partners = T("partners", Column("id", String(40), primary_key=True), Column("data", Text), Column("updated_at", String(40)))
events = T("events", Column("id", Integer, primary_key=True, autoincrement=True), Column("stage", String(40)), Column("scheme_id", String(40)), Column("ts", String(40)))
users = T("users", Column("id", String(40), primary_key=True), Column("phone_hash", String(64), unique=True), Column("phone_enc", Text), Column("role", String(20)), Column("partner_id", String(40)), Column("created_at", String(40)))
partner_users = T("partner_users", Column("phone_hash", String(64), primary_key=True), Column("partner_id", String(40)))
otps = T("otps", Column("id", Integer, primary_key=True, autoincrement=True), Column("phone_hash", String(64), index=True), Column("code_hash", String(64)), Column("expires_at", String(40)), Column("attempts", Integer, default=0), Column("created_at", String(40)))
profiles = T("profiles", Column("user_id", String(40), primary_key=True), Column("data_enc", Text), Column("consent_version", String(20)), Column("consent_at", String(40)), Column("updated_at", String(40)))
referrals = T("referrals", Column("id", String(40), primary_key=True), Column("user_id", String(40), index=True), Column("partner_id", String(40), index=True), Column("scheme_id", String(40)), Column("status", String(30)), Column("share_contact", Boolean), Column("snapshot_enc", Text), Column("created_at", String(40)), Column("updated_at", String(40)))


def now(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat(timespec="seconds")


@contextmanager
def _t(c=None):
    if c is not None:
        yield c
    else:
        with engine.begin() as x:
            yield x


def _rows(q):
    with engine.connect() as c:
        return [dict(r) for r in c.execute(q).mappings().all()]


def _one(q):
    r = _rows(q)
    return r[0] if r else None


def _upsert(x, table, key_col, key, values):
    if x.execute(select(key_col).where(key_col == key)).first():
        x.execute(update(table).where(key_col == key).values(**values))
    else:
        x.execute(insert(table).values(**{key_col.name: key}, **values))


def init():
    md.create_all(engine)
    with engine.begin() as c:
        if c.execute(select(func.count()).select_from(schemes)).scalar() == 0:
            seed = json.loads((Path(__file__).parent / "seed.json").read_text())
            for s in seed["schemes"]:
                save_scheme(s, "seed", c)
            for p in seed["partners"]:
                p["last_verified"] = (date.today() - timedelta(days=p.pop("verified_days_ago"))).isoformat()
                save_partner(p, c)


# ---- rules + partners ----
def save_scheme(data: dict, editor: str, c=None) -> int:
    with _t(c) as x:
        row = x.execute(select(schemes.c.version).where(schemes.c.id == data["id"])).first()
        v, blob, ts = (row[0] + 1 if row else 1), json.dumps(data), now()
        _upsert(x, schemes, schemes.c.id, data["id"], dict(data=blob, version=v, updated_at=ts))
        x.execute(insert(history).values(id=data["id"], version=v, data=blob, updated_at=ts, editor=editor))
    return v


def save_partner(data: dict, c=None):
    with _t(c) as x:
        _upsert(x, partners, partners.c.id, data["id"], dict(data=json.dumps(data), updated_at=now()))


def list_schemes():
    return [{**json.loads(r["data"]), "version": r["version"], "updated_at": r["updated_at"]} for r in _rows(select(schemes).order_by(schemes.c.id))]


def list_partners():
    return [json.loads(r["data"]) for r in _rows(select(partners).order_by(partners.c.id))]


def history_of(scheme_id: str):
    return [{"version": r["version"], "updated_at": r["updated_at"], "editor": r["editor"], "data": json.loads(r["data"])}
            for r in _rows(select(history).where(history.c.id == scheme_id).order_by(history.c.version.desc()))]


# keep the earlier public name
history_fn = history_of


def log_event(stage: str, scheme_id: str | None):
    with engine.begin() as c:
        c.execute(insert(events).values(stage=stage, scheme_id=scheme_id, ts=now()))


def funnel() -> dict:
    out = {r["stage"]: r["n"] for r in _rows(select(events.c.stage, func.count().label("n")).group_by(events.c.stage))}
    for r in _rows(select(referrals.c.status, func.count().label("n")).group_by(referrals.c.status)):
        out["referral_" + r["status"]] = r["n"]
    return out


# ---- users / OTP ----
def link_partner_user(h: str, partner_id: str):
    with engine.begin() as x:
        _upsert(x, partner_users, partner_users.c.phone_hash, h, dict(partner_id=partner_id))


def partner_for_hash(h: str):
    r = _one(select(partner_users).where(partner_users.c.phone_hash == h))
    return r["partner_id"] if r else None


def upsert_user(h: str, phone_enc: str, role: str, partner_id: str | None) -> dict:
    import uuid
    with engine.begin() as x:
        if x.execute(select(users.c.id).where(users.c.phone_hash == h)).first():
            x.execute(update(users).where(users.c.phone_hash == h).values(role=role, partner_id=partner_id, phone_enc=phone_enc))
        else:
            x.execute(insert(users).values(id=uuid.uuid4().hex, phone_hash=h, phone_enc=phone_enc, role=role, partner_id=partner_id, created_at=now()))
    return _one(select(users).where(users.c.phone_hash == h))


def get_user(uid: str):
    return _one(select(users).where(users.c.id == uid))


def otp_add(h, code_hash, expires):
    with engine.begin() as c:
        c.execute(insert(otps).values(phone_hash=h, code_hash=code_hash, expires_at=expires, attempts=0, created_at=now()))


def otp_count_since(h, since) -> int:
    with engine.connect() as c:
        return c.execute(select(func.count()).select_from(otps).where(otps.c.phone_hash == h, otps.c.created_at >= since)).scalar()


def otp_latest(h):
    return _one(select(otps).where(otps.c.phone_hash == h).order_by(otps.c.id.desc()).limit(1))


def otp_attempt(oid: int):
    with engine.begin() as c:
        c.execute(update(otps).where(otps.c.id == oid).values(attempts=otps.c.attempts + 1))


def otp_clear(h):
    with engine.begin() as c:
        c.execute(delete(otps).where(otps.c.phone_hash == h))


# ---- profiles (encrypted) + referrals ----
def profile_set(uid, data_enc, version):
    with engine.begin() as x:
        _upsert(x, profiles, profiles.c.user_id, uid, dict(data_enc=data_enc, consent_version=version, consent_at=now(), updated_at=now()))


def profile_get(uid):
    return _one(select(profiles).where(profiles.c.user_id == uid))


def delete_user(uid):
    """Erase the account, its profile and referrals (DPDP right to erasure)."""
    with engine.begin() as c:
        for t, col in ((referrals, referrals.c.user_id), (profiles, profiles.c.user_id), (users, users.c.id)):
            c.execute(delete(t).where(col == uid))


def referral_add(uid, partner_id, scheme_id, share, snapshot_enc) -> str:
    import uuid
    rid = uuid.uuid4().hex
    with engine.begin() as c:
        c.execute(insert(referrals).values(id=rid, user_id=uid, partner_id=partner_id, scheme_id=scheme_id, status="referred",
                                           share_contact=share, snapshot_enc=snapshot_enc, created_at=now(), updated_at=now()))
    return rid


def referrals_for_user(uid):
    return _rows(select(referrals).where(referrals.c.user_id == uid).order_by(referrals.c.created_at.desc()))


def referrals_for_partner(pid):
    return _rows(select(referrals).where(referrals.c.partner_id == pid).order_by(referrals.c.created_at.desc()))


def referral_get(rid):
    return _one(select(referrals).where(referrals.c.id == rid))


def referral_status(rid, status):
    with engine.begin() as c:
        c.execute(update(referrals).where(referrals.c.id == rid).values(status=status, updated_at=now()))
