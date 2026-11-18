# Pilot proposal: Smart Sahayak (draft for NSFDC / State Channelising Agency)

**Ask:** a 6-month, single-district pilot (suggested: Rewa, Madhya Pradesh) with the State Channelising Agency and 2-3 channel partners.

**Problem:** NSFDC works through channel partners, so applicants must already know which scheme and which partner fit them. Misrouted and incomplete applications are avoidable rejections.

**What we provide (no cost to beneficiaries):** an assisted + self-service tool that checks eligibility, shows EMI before applying, ranks nearby partners, and hands over a pre-filled checklist. Rules are read from a versioned database that your nominated officer controls. We never approve or reject loans.

**What we need from you:** (1) a named officer to confirm scheme rules each quarter, (2) partner branch details and fund-availability signals, (3) permission to use official scheme names and a referral path to PM-SURAJ / SCA offices.

**Pilot metrics (from our KPI slide):** scheme-fit rate, first-route success, median discovery time, partner data freshness, funnel: recommended -> referred -> applied -> approved -> disbursed. Anonymous counts only.

**Data protection:** inputs to `/api/match` are not stored; only anonymous funnel counts are. No Aadhaar numbers are collected.
