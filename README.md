# स्मार्ट Sahayak: AI-Driven Scheme Match for Marginalized Entrepreneurs
Smart India Hackathon 2026 · SIH26092 · Team ByteForge

Matches a citizen's goal to the right concessional scheme, EMI and nearest suitable channel partner. NSFDC lends only through channel partners, so Smart Sahayak is a **discovery and routing layer**: it never approves loans.

## Architecture
- `backend/` FastAPI + PostgreSQL (SQLite file fallback for quick local runs)
  - `engine.py` deterministic, explainable eligibility, EMI and partner routing (40 coverage / 25 distance / 15 data freshness / 20 fund capacity)
  - `db.py` versioned scheme rules with audit history, partner records, anonymous funnel counters
  - `security.py` / `accounts.py` OTP login (hashed numbers, rate limits, lockout), JWT sessions, encrypted saved profiles with consent + erasure, referrals, partner self-service
  - `main.py` public API (`/api/match`, `/api/schemes`, `/api/events`) and key-protected admin API
- `frontend/index.html` bilingual UI; calls the API and falls back to an offline demo engine if no server
- `frontend/admin.html` admin console to edit rules and partners
- `frontend/partner.html` partner portal: confirm schemes/fund availability, work referrals
- `docs/` pilot proposal and compliance checklist

## Run with PostgreSQL (Docker)
```bash
ADMIN_KEY=choose-a-key docker compose up --build   # http://localhost:8000 (OTP shown on screen in this demo setup)
```
Link a branch officer: `curl -XPOST localhost:8000/api/admin/partner-users -H 'X-Admin-Key: ...' -H 'content-type: application/json' -d '{"partner_id":"p1","phone":"98XXXXXXXX"}'`, then sign in at `/partner.html`.

## Run locally
```bash
pip install -r backend/requirements-dev.txt
export ADMIN_KEY="a-long-random-string"
cd backend && uvicorn app.main:app --reload     # http://localhost:8000  (admin: /admin.html)
pytest -q                                        # run tests
```
Docker: `docker build -t sahayak . && docker run -p 8000:8000 -e ADMIN_KEY=... -v sahayak-data:/data sahayak`

After editing `backend/app/seed.json`, run `python scripts/sync_demo_seed.py` to refresh the offline demo data.

## Data status (important)
Scheme figures were taken from official and secondary sources in 2026. Every scheme is `verified: false` until an officer checks it against the current circular and sets `verified_on`; the UI warns users about unverified figures. Partner branches are **sample data**.

## Roadmap
See `docs/PRODUCTION_CHECKLIST.md` for everything still needed before real use.

MIT License
