> **Superseded draft (archived).** Do not cite this document as current policy.
> Canonical policy: **[PRIVACY.md](../../../PRIVACY.md)** at the repository root (also published via the landing site).

---

# UAH Privacy Policy

**Effective Date:** April 15, 2026
**Last Updated:** April 15, 2026

---

## About This Policy

UAH (Unified Application Hub) is an independent, not-for-profit, open source project built by students at the University of Massachusetts Lowell. UAH is not affiliated with, endorsed by, or operated by UMass Lowell.

This Privacy Policy describes how UAH collects, uses, stores, and protects your information. We've written it in plain English intentionally — you deserve to actually understand what happens to your data.

**This policy is currently a working draft.** UAH is in active beta. This policy will be reviewed by legal counsel before final publication.

---

## Our Core Commitments

Before the details, here are the things we will never do — full stop:

- Sell your data to anyone, ever
- Share your data with third parties for profit
- Use your data for targeted advertising
- Run any advertising on UAH whatsoever
- Store your ATS or job portal credentials on our servers
- Store the content of your emails on our servers
- Soft-delete your data (when you delete, it's gone)

These are not just policy statements — several of them are enforced architecturally. The Vault, for example, is designed so that your credentials physically cannot reach our servers.

---

## 1. Who We Are

**Project:** UAH (Unified Application Hub)
**Type:** Independent, not-for-profit, open source student project
**Lead:** Trent Brown and UAH Contributors
**Contact:** admincontact@uahapp.com
**Data requests:** data@uahapp.com
**Repository:** github.com/GUI2-G6/UAH

UAH is not a company. It is not affiliated with UMass Lowell. It is an independent project built by students, operated on a cost-recovery basis through voluntary donations.

---

## 2. What Data We Collect

We collect the minimum data necessary to provide UAH's features. Here is exactly what we collect, broken out by feature:

### Account (Required)
| Data | Why |
|---|---|
| Email address | Primary identity, login, notifications |
| Password (hashed) | Authentication — never stored in plaintext |
| Account creation date | Internal record keeping |

We do not collect your real name, phone number, address, or any demographic information for account creation.

### Application Tracking (Core Feature)
| Data | Why |
|---|---|
| Job title, company, status | To display your tracked applications |
| Application date | To show timeline |
| Notes you add | Stored at your request |

### Vault (Optional, Local-Only)
The Vault is an optional Electron desktop app. It runs entirely on your device.

- **Your ATS credentials are never sent to UAH servers.** They are stored in your device's OS keychain only.
- If you choose to sync application status data, only structured status records are sent: company name, role, status, and date.
- Raw HTML, session tokens, and credentials never leave your device under any circumstance.
- This is enforced architecturally, not just by policy.

### Email Scanning (Optional, OAuth)
If you choose to connect your email for job update scanning:

- UAH requests read-only OAuth access with the minimum viable scope
- We scan only for job-related emails from known ATS senders
- Email content is never stored on UAH servers
- Only extracted status data is retained (e.g. "Interview scheduled — Acme Corp")
- You can revoke access at any time from your Google account settings

### Dedicated Apply Address — apply.uahapp.com (Optional)
If you choose to use a UAH apply address:

- You receive a forwarding address at `[username]@apply.uahapp.com`
- Inbound email is forwarded to your real address
- UAH receives a copy for parsing job-related status signals only
- Raw email content is deleted within hours of parsing — it is never stored
- Your real email address is never revealed to employers unless you choose to share it

### Analytics
UAH uses **Plausible Analytics** — a privacy-respecting analytics tool that collects no personal data, uses no cookies, and is GDPR compliant by design. We use it to understand aggregate usage patterns (page views, feature usage) only.

---

## 3. What We Do Not Collect

To be explicit:

- We do not collect your real name (unless you provide it voluntarily)
- We do not collect payment information (UAH is free)
- We do not collect your location beyond what you voluntarily enter
- We do not collect biometric data
- We do not build advertising profiles
- We do not use tracking pixels or third-party advertising scripts

---

## 4. How We Use Your Information

We use your data only to:

- Provide and improve UAH's features
- Authenticate your account
- Send service-related notifications (e.g. application status updates)
- Understand aggregate usage patterns via Plausible Analytics
- Respond to your support or data requests

We do not use your data for marketing, profiling, or any purpose beyond operating UAH.

---

## 5. Resume Parsing — Third-Party API (Temporary)

UAH offers an optional resume parsing feature that extracts structured information from uploaded resumes to assist with application tracking. We want to be completely transparent about how this currently works.

**Why a third-party API is involved at all:**
UAH's preferred architecture is fully local inference — running AI models on our own servers so resume content never leaves our infrastructure. We have validated this works well: our local stack running GLM-based models on dedicated hardware outperforms cloud alternatives in both speed and privacy. However, our current production server runs an AMD RX 580 GPU which lacks the driver support required for our local inference stack. Our primary inference hardware (an RTX 4080) is temporarily unavailable for 24/7 server use while we finalize a dedicated server GPU upgrade (an RTX 3060 12GB, targeting summer 2026).

Until that upgrade is complete, UAH uses the **Z.ai API** (operated by JINGSHENG HENGXING TECHNOLOGY PTE.LTD, Singapore) as a stopgap for resume parsing only. This is not our preferred or permanent solution — it is a temporary measure to maintain user experience during beta.

**What happens when you use resume parsing right now:**
- Your resume content is transmitted to Z.ai's servers in Singapore for real-time processing
- Per Z.ai's Data Processing Addendum, they do not store your content — it is processed in real-time and not retained on their servers
- Z.ai explicitly states they do not use API customer data to train their models
- UAH stores only the structured output (parsed fields like job titles, dates, skills) — not the raw resume content
- No resume content is shared with any other third party

**What this means for you:**
- If you are not comfortable with resume content being processed via a third-party API based in Singapore, we recommend using manual entry instead — UAH is fully usable without the resume parsing feature
- The feature is entirely optional and clearly labeled as using cloud processing while local inference is unavailable

**Our commitment:**
Once our local inference infrastructure is in place (targeted summer 2026), resume parsing will run entirely on UAH's own servers. No resume content will ever leave our infrastructure. We will update this policy and notify users when this transition is complete.

---

## 6. Third Parties

UAH uses a small number of third-party services to operate. Here is each one and what they receive:

| Service | Purpose | Data Shared |
|---|---|---|
| **Google OAuth** | Optional login and email scanning | Email address, OAuth token |
| **Cloudflare** | Infrastructure, security, DNS, email routing | IP address, request metadata |
| **Plausible Analytics** | Privacy-respecting usage analytics | No personal data |
| **Z.ai API** (temporary) | Resume parsing — cloud fallback only | Resume content, processed in real-time, not stored per their DPA. Singapore-based. See Section 5. |
| **WhatJobs** (when live) | Job listing data via FeedAPI | No user data shared with WhatJobs |

We do not share your personal data with job boards or listing providers. Traffic sent to partner job boards (clicks on listings) is standard web traffic — no personal data is transmitted.

---

## 7. Data Storage & Security

- User data is stored on servers operated by UAH, hosted on infrastructure in the United States
- Passwords are hashed using bcrypt — never stored in plaintext
- All connections use HTTPS/TLS encryption
- API endpoints are protected by rate limiting and Cloudflare WAF
- `.env` files and secrets are never committed to the public repository
- We conduct regular security audits of our infrastructure

---

## 8. Your Rights

You have the following rights regarding your data:

**Access** — You can request a copy of all data UAH holds about you at any time.

**Correction** — You can correct inaccurate data via your account settings or by contacting us.

**Deletion** — You can delete your account at any time. Deletion is real and permanent — not a soft delete. All associated data is removed within 30 days. Backups are purged on their normal rotation schedule.

**Export (Takeout)** — You can download everything UAH knows about you at any time via the data export feature in your account settings.

**Opt-out** — Each optional feature (email scanning, apply address, vault sync) can be disabled independently at any time from your account settings.

To exercise any of these rights, email **data@uahapp.com** or use the controls in your account settings.

---

## 9. GDPR (EU Users)

If you are located in the European Economic Area:

- Our lawful basis for processing is **legitimate interests** (providing the service you signed up for) and **consent** for optional features
- You have the right to lodge a complaint with your local data protection authority
- You may contact us at data@uahapp.com to exercise any GDPR rights

---

## 10. CCPA (California Users)

UAH does not sell personal information. We do not share personal information with third parties for their direct marketing purposes. California residents may contact data@uahapp.com with any privacy requests.

---

## 11. COPPA (Children)

UAH is not directed at users under the age of 13. We do not knowingly collect personal information from children under 13. If we become aware that a user is under 13, we will delete their account and associated data promptly.

---

## 12. FERPA Notice

UAH is an independent student project. It is not affiliated with, operated by, or acting on behalf of the University of Massachusetts Lowell. UAH does not share any user data with UMass Lowell or any other educational institution.

---

## 13. Cookies

UAH uses minimal cookies required for authentication (session management). We do not use advertising cookies, tracking cookies, or third-party cookies. Plausible Analytics requires no cookies.

---

## 14. Sunset Plan

If UAH ever ceases operation:

- All users will be notified by email at least 30 days before shutdown
- All user data will be permanently deleted within 30 days of shutdown
- The open source codebase will remain publicly available on GitHub

---

## 15. Changes to This Policy

If we make material changes to this policy, we will notify users by email and update the "Last Updated" date at the top of this page. Continued use of UAH after notification constitutes acceptance of the updated policy.

---

## 16. Contact

For any privacy-related questions, data requests, or concerns:

**Email:** data@uahapp.com
**General contact:** admincontact@uahapp.com
**Mailing address:** Not yet established — UAH is a student project without a formal legal entity at this time.

For opt-out requests related to our data scraping policy (if you operate a job board):
See our [Data & Scraping Policy](https://uahapp.com/scraping-policy) or email data@uahapp.com directly.

---

*UAH is a not-for-profit, open source project. We built this because job searching is hard enough without your tools working against you.*

*This policy is a living document and will be reviewed by legal counsel before final publication.*
