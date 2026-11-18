"""OTP, token, encryption and SMS helpers. Secrets come from env; production refuses to start with dev defaults."""
import base64, hashlib, hmac, json, logging, os, re, secrets, time, urllib.request
from collections import defaultdict, deque

import jwt
from cryptography.fernet import Fernet
from fastapi import Header, HTTPException

from . import db

log = logging.getLogger("sahayak")
is_prod = lambda: os.getenv("SAHAYAK_ENV", "dev") == "prod"


def _env(name: str, dev: str) -> str:
    v = os.getenv(name)
    if v:
        return v
    if is_prod():
        raise RuntimeError(f"{name} must be set when SAHAYAK_ENV=prod")
    return dev


def normalize_phone(p: str) -> str:
    m = re.fullmatch(r"(?:\+?91|0)?([6-9]\d{9})", re.sub(r"[\s\-()]", "", p))
    if not m:
        raise HTTPException(422, "Enter a valid 10-digit Indian mobile number")
    return "+91" + m.group(1)


def hash_phone(phone: str) -> str:
    return hmac.new(_env("PEPPER", "dev-pepper").encode(), phone.encode(), hashlib.sha256).hexdigest()


def hash_otp(phone_hash: str, code: str) -> str:
    return hmac.new(_env("PEPPER", "dev-pepper").encode(), (phone_hash + ":" + code).encode(), hashlib.sha256).hexdigest()


def new_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def _fernet() -> Fernet:
    k = _env("DATA_KEY", "dev")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"dev-data-key").digest()) if k == "dev" else k.encode())


enc = lambda s: _fernet().encrypt(s.encode()).decode()
dec = lambda s: _fernet().decrypt(s.encode()).decode()


def send_sms(to: str, message: str):
    """Posts {to, message} to SMS_WEBHOOK_URL (your SMS gateway adapter). In dev without a webhook it only logs."""
    url = os.getenv("SMS_WEBHOOK_URL")
    if url:
        h = {"Content-Type": "application/json"}
        if os.getenv("SMS_WEBHOOK_TOKEN"):
            h["Authorization"] = "Bearer " + os.environ["SMS_WEBHOOK_TOKEN"]
        try:
            urllib.request.urlopen(urllib.request.Request(url, json.dumps({"to": to, "message": message}).encode(), h), timeout=8).read()
        except Exception:
            log.exception("SMS send failed")
            raise HTTPException(503, "Could not send SMS. Try again.")
    elif is_prod():
        raise HTTPException(503, "SMS provider not configured")
    else:
        log.warning("DEV SMS to ***%s: %s", to[-4:], message)


class RateLimiter:
    """In-memory sliding window. Use Redis or the API gateway when running more than one instance."""
    def __init__(self):
        self.hits = defaultdict(deque)

    def hit(self, key: str, limit: int, window: int):
        q, t = self.hits[key], time.time()
        while q and q[0] < t - window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(429, "Too many requests. Please wait and try again.")
        q.append(t)


limiter = RateLimiter()


def make_token(user: dict) -> str:
    claims = {"sub": user["id"], "role": user["role"], "pid": user["partner_id"], "exp": int(time.time()) + 8 * 3600}
    return jwt.encode(claims, _env("JWT_SECRET", "dev-jwt-secret-change-me-32-bytes-min!!"), "HS256")


def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in required")
    try:
        c = jwt.decode(authorization[7:], _env("JWT_SECRET", "dev-jwt-secret-change-me-32-bytes-min!!"), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired. Sign in again.")
    u = db.get_user(c["sub"])
    if not u:
        raise HTTPException(401, "Account not found")
    return u


def require_partner(u: dict = None) -> dict:  # replaced by dependency wrapper in accounts.py
    return u


def admin(x_admin_key: str = Header(default="")) -> str:
    key = os.getenv("ADMIN_KEY", "")
    if not key or not hmac.compare_digest(x_admin_key.encode(), key.encode()):
        raise HTTPException(401, "Invalid or missing admin key")
    return "admin"
