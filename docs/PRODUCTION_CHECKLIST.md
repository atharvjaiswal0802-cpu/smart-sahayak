# What is still needed before real citizens use this

## Must have (blockers)
- [ ] Verify every scheme with NSFDC / SCA, then set `verified: true` + `verified_on` in the admin console
- [ ] Real partner data: replace the sample branches with onboarded partners (admin links each branch officer's phone via `POST /api/admin/partner-users`)
- [ ] Real SMS: gateway adapter behind `SMS_WEBHOOK_URL`; in India, SMS templates and sender IDs must be registered under TRAI DLT
- [ ] Database migrations (Alembic) instead of `create_all`; automated encrypted backups; tested restore
- [ ] Secrets in a secret manager; `SAHAYAK_ENV=prod`; HTTPS only; key-rotation plan for `DATA_KEY` and `JWT_SECRET`
- [ ] Session hardening: httpOnly + Secure + SameSite cookies with CSRF protection instead of sessionStorage tokens; security headers/CSP
- [ ] Rate limiting at the gateway (the built-in limiter is per-process); bot protection on OTP request; SMS cost alarms
- [ ] Individual admin accounts with roles and audit log (the single `ADMIN_KEY` is pilot-only); audit log for partner access to applicant data
- [ ] Privacy notice and consent text in each supported language, reviewed by counsel; retention and deletion schedule; DPIA
- [ ] Independent security audit / penetration test

## Should have
- [ ] SMS/email notifications when referral status changes (citizen side)
- [ ] Road-distance routing (Google Maps or OSM) instead of straight-line distance
- [ ] More languages (Hindi done; add regional languages) and voice/IVR flow
- [ ] Deep link / handoff to PM-SURAJ and JanSamarth where an online route exists
- [ ] Aadhaar/DigiLocker document fetch (requires approved access and agreements)
- [ ] Monitoring (logs, metrics, uptime alerts), error tracking, load test
- [ ] Browser end-to-end tests (Playwright), accessibility audit with a screen reader on low-end Android
- [ ] Analytics dashboard for the KPI funnel; CONTRIBUTING.md, SECURITY.md, issue templates
- [ ] Infrastructure as code and a staging environment
