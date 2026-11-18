# स्मार्ट Sahayak – AI-Driven Scheme Match for Marginalized Entrepreneurs
Smart India Hackathon 2026 · Problem Statement SIH26092 · Team ByteForge

A multilingual (English/Hindi) web prototype that turns a citizen's goal into the right concessional scheme, EMI, and nearest eligible channel partner.

## Features
- Rule-based eligibility engine with explainable reasons per scheme
- Ranking by rate, funding support and EMI affordability
- EMI calculator and 12-month repayment schedule
- Partner routing (scheme compatibility 50 / proximity 30 / data freshness 20) using browser GPS + haversine distance
- Document checklist, demo application and status tracker
- Assisted mode (larger text, read-aloud) and Hindi/English toggle

## Run
No build step. Open `index.html` in a browser, or `python3 -m http.server` and visit http://localhost:8000.

## Deploy (GitHub Pages)
Repo Settings → Pages → Deploy from branch `main` / root.

## Data note
Scheme rules, rates and partner branches in the `CONFIG` block of `index.html` are **illustrative sample data**. Replace with live NSFDC / JanSamarth / Stand-Up India / partner APIs and verify against official notices before real use.

## Roadmap (from the SIH technical approach)
Mobile OTP + Aadhaar/DigiLocker, FastAPI + PostgreSQL backend, scikit-learn/LLM matching, Google Maps/OSM routing, SMS/IVR, offline sync.

## License
MIT
