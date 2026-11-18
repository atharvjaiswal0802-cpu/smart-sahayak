# स्मार्ट Sahayak: AI-Driven Scheme Match for Marginalized Entrepreneurs
Smart India Hackathon 2026 · SIH26092 · Team ByteForge

Matches a citizen's goal to the right concessional scheme, EMI and nearest suitable channel partner. NSFDC lends only through channel partners, so Smart Sahayak is a **discovery and routing layer**: it never approves loans.

## Architecture
- `backend/` FastAPI + SQLite (swap for PostgreSQL in production)
  - `engine.py` deterministic, explainable eligibility, EMI and partner routing (40 coverage / 25 distance / 15 data freshness / 20 fund capacity)
  - `db.py` versioned scheme rules with audit history, partner records, anonymous funnel counters
  - `main.py` public API (`/api/match`, `/api/schemes`, `/api/events`) and key-protected admin API
- `frontend/index.html` bilingual UI; calls the API and falls back to an offline demo engine if no server
- `frontend/admin.html` admin console to edit rules and partners
- `docs/` pilot proposal and compliance checklist

## Run locally
```bash
pip install -r backend/requirements.txt
export ADMIN_KEY="a-long-random-string"
cd backend && uvicorn app.main:app --reload     # http://localhost:8000  (admin: /admin.html)
pytest -q                                        # run tests
```
Docker: `docker build -t sahayak . && docker run -p 8000:8000 -e ADMIN_KEY=... -v sahayak-data:/data sahayak`

After editing `backend/app/seed.json`, run `python scripts/sync_demo_seed.py` to refresh the offline demo data.

## Data status (important)
Scheme figures were taken from official and secondary sources in 2026. Every scheme is `verified: false` until an officer checks it against the current circular and sets `verified_on`; the UI warns users about unverified figures. Partner branches are **sample data**.

## Roadmap
OTP login, DigiLocker, PostgreSQL, partner self-service portal, SMS/IVR, regional languages, map routing, offline sync. See `docs/`.

MIT License
