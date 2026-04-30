# Historical Snapshot: Endpoint Utilization Audit (Active Runtime Scope)

This audit captured route usage on 2026-04-11. It is preserved for historical context and should not be treated as the current product roadmap or API usage matrix.

Use these active docs first:

- [../../backend/README.md](../../backend/README.md)
- [../../frontend/README.md](../../frontend/README.md)
- [../../architecture/ARCHITECTURE.md](../../architecture/ARCHITECTURE.md)

# Endpoint Utilization Audit (Active Runtime Scope)

Date: 2026-04-11

Scope rules applied:
- Counted only endpoints called by active routed frontend pages/components/helpers.
- Excluded `frontend/src/lib/localMockApi.js` and `frontend/src/views/old/*`.
- Included practical product opportunities for underused/unused endpoints.

## Coverage Summary

- Total implemented endpoints: **60**
- `Used`: **36**
- `Implemented but unused`: **3**
- `Partially utilized`: **1**
- `Could be utilized more`: **20**

## Canonical Matrix (Every Endpoint Exactly Once)

### Auth

| Method | Path | Backend Source | Frontend Usage Evidence | Status | Opportunity/Recommendation | Priority |
|---|---|---|---|---|---|---|
| PUT | `/api/account/change-email` | `backend/app/api/account.py:123` | `frontend/src/views/Applicant-Information.vue:335; frontend/src/views/Settings.vue:370` | Used | Currently called by active routed frontend. | - |
| PUT | `/api/account/change-name` | `backend/app/api/account.py:214` | `frontend/src/views/Applicant-Information.vue:267; frontend/src/views/Resumes.vue:1838` | Used | Currently called by active routed frontend. | - |
| PUT | `/api/account/change-password` | `backend/app/api/account.py:95` | `frontend/src/views/Applicant-Information.vue:300; frontend/src/views/Settings.vue:324` | Used | Currently called by active routed frontend. | - |
| PUT | `/api/account/change-username` | `backend/app/api/account.py:188` | `frontend/src/views/Applicant-Information.vue:380; frontend/src/views/Settings.vue:422` | Used | Currently called by active routed frontend. | - |
| DELETE | `/api/account/delete` | `backend/app/api/account.py:313` | `frontend/src/views/Applicant-Information.vue:449; frontend/src/views/Settings.vue:494` | Used | Currently called by active routed frontend. | - |
| POST | `/api/account/forgot-password` | `backend/app/api/account.py:23` | `frontend/src/views/Forgot-Password.vue:55` | Used | Currently called by active routed frontend. | - |
| POST | `/api/account/reset-password` | `backend/app/api/account.py:69` | `frontend/src/views/Reset-Password.vue:85` | Used | Currently called by active routed frontend. | - |
| POST | `/api/account/send-verification` | `backend/app/api/account.py:237` | `frontend/src/views/Applicant-Information.vue:406; frontend/src/views/Settings.vue:451` | Used | Currently called by active routed frontend. | - |
| POST | `/api/account/verify-email` | `backend/app/api/account.py:287` | `frontend/src/views/Applicant-Information.vue:423; frontend/src/views/Settings.vue:468` | Used | Currently called by active routed frontend. | - |
| GET | `/api/auth/google` | `backend/app/api/routes.py:2108` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Add "Sign in with Google" CTA on Login/Register. | P1 |
| GET | `/api/auth/google/callback` | `backend/app/api/routes.py:2180` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Complete browser OAuth redirect flow and token handoff in frontend auth module. | P1 |
| POST | `/api/auth/login` | `backend/app/api/auth.py:110` | `frontend/src/views/Login.vue:68` | Used | Currently called by active routed frontend. | - |
| GET | `/api/auth/me` | `backend/app/api/auth.py:188` | `frontend/src/views/Applicant-Information.vue:247; frontend/src/views/Settings.vue:263` | Used | Currently called by active routed frontend. | - |
| POST | `/api/auth/register` | `backend/app/api/auth.py:64` | `frontend/src/views/Register.vue:81` | Used | Currently called by active routed frontend. | - |
| POST | `/api/auth/token` | `backend/app/api/auth.py:149` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Implemented but unused | Used for Swagger/tooling OAuth2 flow, not current site UX. | P2 |

### Jobs & Geolocation

| Method | Path | Backend Source | Frontend Usage Evidence | Status | Opportunity/Recommendation | Priority |
|---|---|---|---|---|---|---|
| GET | `/api/geolocation/cities-in-radius` | `backend/app/api/routes.py:1267` | `frontend/src/views/Job-Board.vue:1604` | Used | Currently called by active routed frontend. | - |
| GET | `/api/geolocation/country-cities` | `backend/app/api/routes.py:1342` | `frontend/src/views/Job-Board.vue:1563` | Used | Currently called by active routed frontend. | - |
| GET | `/api/geolocation/geocode` | `backend/app/api/routes.py:1144` | `frontend/src/views/Job-Board.vue:1510; frontend/src/views/Job-Board.vue:1529` | Used | Currently called by active routed frontend. | - |
| GET | `/api/geolocation/ip` | `backend/app/api/routes.py:1082` | `frontend/src/views/Job-Board.vue:1460` | Used | Currently called by active routed frontend. | - |
| GET | `/api/geolocation/muse-supported-countries` | `backend/app/api/routes.py:1392` | `frontend/src/views/Job-Board.vue:1135` | Used | Currently called by active routed frontend. | - |
| GET | `/api/geolocation/muse-supported-locations` | `backend/app/api/routes.py:1432` | `frontend/src/views/Job-Board.vue:1562` | Used | Currently called by active routed frontend. | - |
| POST | `/api/geolocation/muse-supported-locations/refresh` | `backend/app/api/routes.py:1482` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Implemented but unused | No active runtime caller; operational refresh hook for index maintenance. | P2 |
| GET | `/api/geolocation/reverse` | `backend/app/api/routes.py:1217` | `frontend/src/views/Job-Board.vue:1481` | Used | Currently called by active routed frontend. | - |
| GET | `/api/jobs/filter-metadata` | `backend/app/api/routes.py:1508` | `frontend/src/views/Job-Board.vue:1124` | Used | Currently called by active routed frontend. | - |
| POST | `/api/jobs/save` | `backend/app/api/routes.py:1995` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Add "Save job" action on job cards/details. | P1 |
| GET | `/api/jobs/saved` | `backend/app/api/routes.py:2055` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Add Saved Jobs view with persisted shortlist. | P1 |
| DELETE | `/api/jobs/saved/{job_id}` | `backend/app/api/routes.py:2080` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Enable unsave/remove action from Saved Jobs list. | P1 |
| GET | `/api/jobs/search` | `backend/app/api/routes.py:1561` | `frontend/src/views/Job-Board.vue:1699` | Used | Currently called by active routed frontend. | - |

### Resume

| Method | Path | Backend Source | Frontend Usage Evidence | Status | Opportunity/Recommendation | Priority |
|---|---|---|---|---|---|---|
| GET | `/api/resume/` | `backend/app/api/resume.py:421` | `frontend/src/views/Resumes.vue:1258` | Used | Currently called by active routed frontend. | - |
| GET | `/api/resume/parse-job/{job_id}` | `backend/app/api/resume.py:645` | `frontend/src/views/Resumes.vue:1488` | Used | Currently called by active routed frontend. | - |
| POST | `/api/resume/parse-job/{job_id}/cancel` | `backend/app/api/resume.py:703` | `frontend/src/views/Resumes.vue:1546` | Used | Currently called by active routed frontend. | - |
| GET | `/api/resume/queue/status` | `backend/app/api/resume.py:629` | `frontend/src/views/Resumes.vue:1165` | Used | Currently called by active routed frontend. | - |
| POST | `/api/resume/upload` | `backend/app/api/resume.py:249` | `frontend/src/views/Resumes.vue:1445` | Used | Currently called by active routed frontend. | - |
| DELETE | `/api/resume/{resume_id}` | `backend/app/api/resume.py:531` | `frontend/src/views/Resumes.vue:1296` | Used | Currently called by active routed frontend. | - |
| GET | `/api/resume/{resume_id}` | `backend/app/api/resume.py:444` | `frontend/src/views/Resumes.vue:1313` | Used | Currently called by active routed frontend. | - |
| POST | `/api/resume/{resume_id}/parse` | `backend/app/api/resume.py:337` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Add optional synchronous "Parse now" action for immediate/manual parse workflows. | P2 |
| POST | `/api/resume/{resume_id}/parse-async` | `backend/app/api/resume.py:568` | `frontend/src/views/Resumes.vue:1456` | Used | Currently called by active routed frontend. | - |
| GET | `/api/resume/{resume_id}/pdf` | `backend/app/api/resume.py:469` | `frontend/src/views/Resumes.vue:1218` | Used | Currently called by active routed frontend. | - |
| GET | `/api/resume/{resume_id}/portal-check` | `backend/app/api/resume.py:497` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Show missing-required-fields checklist before apply/autofill actions. | P1 |

### Profiles

| Method | Path | Backend Source | Frontend Usage Evidence | Status | Opportunity/Recommendation | Priority |
|---|---|---|---|---|---|---|
| GET | `/api/applicant-profile/` | `backend/app/api/applicant_profile.py:18` | `frontend/src/views/Resumes.vue:1562; frontend/src/views/Resumes.vue:1755` | Used | Currently called by active routed frontend. | - |
| POST | `/api/applicant-profile/` | `backend/app/api/applicant_profile.py:65` | `frontend/src/views/Resumes.vue:1625; frontend/src/views/Resumes.vue:1764` | Used | Currently called by active routed frontend. | - |
| GET | `/api/applicant-profile/active` | `backend/app/api/applicant_profile.py:41` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Load active profile directly instead of deriving from list each time. | P2 |
| DELETE | `/api/applicant-profile/{profile_id}` | `backend/app/api/applicant_profile.py:190` | `frontend/src/views/Resumes.vue:1799` | Used | Currently called by active routed frontend. | - |
| GET | `/api/applicant-profile/{profile_id}` | `backend/app/api/applicant_profile.py:102` | `frontend/src/views/Resumes.vue:1645` | Used | Currently called by active routed frontend. | - |
| PUT | `/api/applicant-profile/{profile_id}` | `backend/app/api/applicant_profile.py:125` | `frontend/src/views/Resumes.vue:1822; frontend/src/views/Resumes.vue:1887` | Used | Currently called by active routed frontend. | - |
| POST | `/api/applicant-profile/{profile_id}/activate` | `backend/app/api/applicant_profile.py:156` | `frontend/src/views/Resumes.vue:1743` | Used | Currently called by active routed frontend. | - |

### Integrations

| Method | Path | Backend Source | Frontend Usage Evidence | Status | Opportunity/Recommendation | Priority |
|---|---|---|---|---|---|---|
| GET | `/api/integrations/gmail/callback` | `backend/app/api/gmail.py:63` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Handle OAuth callback route and post-connect UX state. | P1 |
| GET | `/api/integrations/gmail/connect` | `backend/app/api/gmail.py:41` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Add Gmail connect CTA in Settings integrations section. | P1 |
| DELETE | `/api/integrations/gmail/disconnect` | `backend/app/api/gmail.py:119` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Provide disconnect control for token revocation/account hygiene. | P1 |
| POST | `/api/integrations/gmail/scan` | `backend/app/api/gmail.py:173` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Allow mailbox scan to auto-surface application/interview updates. | P1 |
| GET | `/api/integrations/gmail/status` | `backend/app/api/gmail.py:111` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Display Gmail connection state in Settings. | P1 |

### Apply Sessions

| Method | Path | Backend Source | Frontend Usage Evidence | Status | Opportunity/Recommendation | Priority |
|---|---|---|---|---|---|---|
| GET | `/api/apply-sessions/` | `backend/app/api/apply_session.py:115` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Populate Timeline page with recent apply sessions. | P2 |
| POST | `/api/apply-sessions/start` | `backend/app/api/apply_session.py:37` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Create apply session when user opens external application flow. | P1 |
| GET | `/api/apply-sessions/{session_id}` | `backend/app/api/apply_session.py:143` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Show per-application event detail and completion diagnostics. | P2 |
| POST | `/api/apply-sessions/{session_id}/events` | `backend/app/api/apply_session.py:60` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Log step-level events (autofill/manual edits/errors) during application flow. | P1 |
| POST | `/api/apply-sessions/{session_id}/finalize` | `backend/app/api/apply_session.py:85` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Record submitted/abandoned outcomes and funnel metrics. | P1 |

### Diagnostics & Core

| Method | Path | Backend Source | Frontend Usage Evidence | Status | Opportunity/Recommendation | Priority |
|---|---|---|---|---|---|---|
| GET | `/api/` | `backend/app/main.py:311` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Implemented but unused | No active runtime caller; keep as service discovery endpoint for ops/dev tools. | P2 |
| GET | `/api/diagnostics` | `backend/app/api/routes.py:2305` | `frontend/src/views/Status.vue:249` | Partially utilized | Called from public Status page without bearer auth; switch to authed request for admins and add non-admin fallback to /api/status. | P0 |
| GET | `/api/health` | `backend/app/main.py:325` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Use for lightweight heartbeat badges and periodic frontend health polling. | P1 |
| GET | `/api/status` | `backend/app/api/routes.py:2263` | `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv` | Could be utilized more | Use as the default unauthenticated probe for the Status page before gated diagnostics. | P0 |

## Implemented but Unused Endpoints

### Auth

- `POST /api/auth/token`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P2
  - Recommendation: Used for Swagger/tooling OAuth2 flow, not current site UX.

### Jobs & Geolocation

- `POST /api/geolocation/muse-supported-locations/refresh`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P2
  - Recommendation: No active runtime caller; operational refresh hook for index maintenance.

### Diagnostics & Core

- `GET /api/`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P2
  - Recommendation: No active runtime caller; keep as service discovery endpoint for ops/dev tools.

## Partially Utilized Endpoints

### Diagnostics & Core

- `GET /api/diagnostics`
  - Evidence: `frontend/src/views/Status.vue:249`
  - Priority: P0
  - Recommendation: Called from public Status page without bearer auth; switch to authed request for admins and add non-admin fallback to /api/status.

## Could-Be-Utilized-More Opportunities

### Auth

- `GET /api/auth/google`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Add "Sign in with Google" CTA on Login/Register.
- `GET /api/auth/google/callback`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Complete browser OAuth redirect flow and token handoff in frontend auth module.

### Jobs & Geolocation

- `POST /api/jobs/save`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Add "Save job" action on job cards/details.
- `GET /api/jobs/saved`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Add Saved Jobs view with persisted shortlist.
- `DELETE /api/jobs/saved/{job_id}`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Enable unsave/remove action from Saved Jobs list.

### Resume

- `POST /api/resume/{resume_id}/parse`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P2
  - Recommendation: Add optional synchronous "Parse now" action for immediate/manual parse workflows.
- `GET /api/resume/{resume_id}/portal-check`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Show missing-required-fields checklist before apply/autofill actions.

### Profiles

- `GET /api/applicant-profile/active`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P2
  - Recommendation: Load active profile directly instead of deriving from list each time.

### Integrations

- `GET /api/integrations/gmail/callback`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Handle OAuth callback route and post-connect UX state.
- `GET /api/integrations/gmail/connect`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Add Gmail connect CTA in Settings integrations section.
- `DELETE /api/integrations/gmail/disconnect`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Provide disconnect control for token revocation/account hygiene.
- `POST /api/integrations/gmail/scan`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Allow mailbox scan to auto-surface application/interview updates.
- `GET /api/integrations/gmail/status`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Display Gmail connection state in Settings.

### Apply Sessions

- `GET /api/apply-sessions/`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P2
  - Recommendation: Populate Timeline page with recent apply sessions.
- `POST /api/apply-sessions/start`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Create apply session when user opens external application flow.
- `GET /api/apply-sessions/{session_id}`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P2
  - Recommendation: Show per-application event detail and completion diagnostics.
- `POST /api/apply-sessions/{session_id}/events`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Log step-level events (autofill/manual edits/errors) during application flow.
- `POST /api/apply-sessions/{session_id}/finalize`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Record submitted/abandoned outcomes and funnel metrics.

### Diagnostics & Core

- `GET /api/health`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P1
  - Recommendation: Use for lightweight heartbeat badges and periodic frontend health polling.
- `GET /api/status`
  - Evidence: `No active call in docs/backend/endpoint_inventory_frontend_calls.tsv`
  - Priority: P0
  - Recommendation: Use as the default unauthenticated probe for the Status page before gated diagnostics.

## Evidence Notes

- Backend inventory source: `docs/archive/backend/endpoint_inventory_backend.tsv`.
- Frontend active-call inventory source: `docs/archive/backend/endpoint_inventory_frontend_calls.tsv`.
- Active runtime route scope source: `frontend/src/router/index.js`.
