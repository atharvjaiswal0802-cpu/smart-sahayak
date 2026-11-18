# Compliance checklist (confirm with legal counsel before launch)

- [ ] DPDP Act 2023: notice + consent in the user's language before collecting profile data; purpose limitation; deletion on request; grievance contact
- [ ] Caste, income and location are sensitive: collect only what the rules need, never store in analytics, encrypt at rest once profiles exist
- [ ] Aadhaar: do not store numbers; use DigiLocker / authorised e-KYC only
- [ ] Host in India; set `ADMIN_KEY` from a secret manager; add HTTPS, rate limiting, and login (OTP) before storing profiles
- [ ] Independent security audit (CERT-In empanelled auditor) before public launch
- [ ] Accessibility: GIGW / WCAG 2.1 AA; test with screen reader and low-end Android
- [ ] Rules governance: each scheme `verified=true` only with `verified_on` date and `source_url`; keep the version history
- [ ] Ranking integrity: no commissions or paid placement from lenders
