# Server Environment Checklist

This checklist groups the server-side env keys that matter most for reliable UAH operation.

Treat it as an operator-facing summary. The detailed variable set still lives in:

- `backend/app/core/config.py`
- `env-examples/*/.env.example`
- compose files and lifecycle scripts

## Always Required

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `SESSION_SECRET`

These are the top-level secrets the backend refuses to start without. Cookie
and auth namespace settings are still required, but they are grouped under Core
Runtime Identity because they define environment-scoped runtime behavior.

## Core Runtime Identity

- `ENV`
- `ENVIRONMENT`
- `COMPOSE_PROJECT_NAME`
- `PUBLIC_APP_URL`
- `AUTH_NAMESPACE`
- `AUTH_COOKIE_NAME`
- `SESSION_COOKIE_NAME`
- `SESSION_COOKIE_SAMESITE`
- `SESSION_COOKIE_PATH`
- `SESSION_COOKIE_HTTPS_ONLY`

These values control environment labeling, cookie naming, and whether generated API docs are enabled.

## Dev / Local Test Account Controls

Document these keys in templates even when disabled:

- `DEV_AUTH_TEST_ACCOUNT_ENABLED`
- `DEV_AUTH_TEST_EMAIL`
- `DEV_AUTH_TEST_USERNAME` (legacy fallback only)
- `DEV_AUTH_TEST_PASSWORD`
- `DEV_AUTH_TEST_FIRST_NAME`
- `DEV_AUTH_TEST_LAST_NAME`
- `DEV_AUTH_TEST_IS_ADMIN`
- `DEV_AUTH_TEST_IS_DEVELOPER`
- `DEV_AUTH_TEST_ROTATE_PASSWORD`

Policy:

- local/dev may enable the seeded account intentionally
- beta/prod should keep it disabled
- if `DEV_AUTH_TEST_USERNAME` is used, it should contain an email value

## OAuth And Account Integrations

### Google sign-in

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

### Gmail integration

- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REDIRECT_URI`
- `GMAIL_TOKEN_ENCRYPTION_KEY`

## Email Delivery

- `EMAILS_ENABLED`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_FROM`
- `SMTP_USE_TLS`
- `SMTP_USE_SSL`
- `SMTP_TIMEOUT_SECONDS`
- `SMTP_USERNAME` and `SMTP_PASSWORD` when the provider requires login

### Public intake notification targets

Optional defaults exist in `backend/app/core/config.py`; set explicitly per environment:

- `BETA_ACCESS_NOTIFY_EMAIL` — beta access request intake (`POST /api/public/beta-access`)
- `LANDING_FEEDBACK_NOTIFY_EMAIL` — landing feedback / wishlist (`POST /api/public/landing-feedback`)

## Job Search Providers

### Primary provider config

- `MUSE_API_KEY`
- `THE_MUSE_API_KEY`
- `THE_MUSE_RATE_LIMIT_PER_HOUR`
- `JOB_PROVIDER_CONTROLS_JSON`

### Optional provider credentials / throttles

- `FINDWORK_API_KEY`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`
- `JOOBLE_API_KEY`
- `ARBEITNOW_INTER_REQUEST_DELAY`
- `FINDWORK_INTER_REQUEST_DELAY`
- `JOOBLE_INTER_REQUEST_DELAY`
- `JOOBLE_PAGE_SIZE`
- `ADZUNA_DAILY_REQUEST_BUDGET`

## Search And Geolocation Controls

Muse pagination / guardrails:

- `MUSE_PAGE_CHASE_ENABLED`
- `MUSE_PAGE_CHASE_MAX_PAGES`
- `MUSE_PAGE_CHASE_MAX_API_CALLS_PER_REQUEST`
- `MUSE_PAGE_CHASE_TARGET_ACCEPTED_RESULTS`
- `MUSE_PAGE_CHASE_MIN_FILTERED_RATIO`
- `MUSE_PAGE_CHASE_TIMEOUT_SECONDS`
- `MUSE_ADAPTIVE_PAGE_CHASE_ENABLED`
- `MUSE_ADAPTIVE_PAGE_CHASE_EXTRA_PAGES`
- `MUSE_ADAPTIVE_PAGE_CHASE_BREADTH_THRESHOLD`
- `MUSE_ADAPTIVE_PAGE_CHASE_MIN_FILTERED_RATIO`
- `MUSE_LOCATION_PARAM_CAP`
- `MUSE_LOCATION_INDEX_ENABLED`
- `MUSE_LOCATION_INDEX_REFRESH_HOURS`
- `MUSE_LOCATION_INDEX_SCAN_MAX_PAGES`
- `MUSE_LOCATION_INDEX_TIMEOUT_SECONDS`
- `MUSE_LOCATION_INDEX_RETENTION_DAYS`
- `CONSTRAINT_COMPATIBILITY_ENABLED`
- `CONSTRAINT_FILTER_MIN_CONFIDENCE`
- `JOBS_DEFAULT_PAGE_SIZE`

Jobs cache and URL validation:

- `JOBS_CACHE_ENABLED`
- `JOBS_CACHE_TTL_SECONDS`
- `JOBS_CACHE_MAX_KEYS`
- `JOBS_URL_VALIDATION_ENABLED`
- `JOBS_URL_VALIDATION_TIMEOUT_SECONDS`
- `JOBS_URL_VALIDATION_MAX_CHECKS_PER_REQUEST`
- `JOBS_URL_VALIDATION_CONCURRENCY`
- `JOBS_URL_VALIDATION_BAD_TTL_SECONDS`
- `JOBS_URL_VALIDATION_GOOD_TTL_SECONDS`
- `JOBS_URL_VALIDATION_UNKNOWN_TTL_SECONDS`
- `JOB_LINK_RECHECK_HOURS`
- `GEO_IP_PROVIDER`
- `IPSTACK_API_KEY`
- `GEOLOCATION_AUTO_BUILD_DATASET`
- `GEOLOCATION_IGNORE_LOCAL_DATASET`
- `GEOLOCATION_DATASET_TIMEOUT_SECONDS`
- `NOMINATIM_USER_AGENT`

## Queue And Background Work

### Enablement and connection

- `REDIS_ENABLED`
- `REDIS_URL`
- `REDIS_HOST_PORT`
- `BETA_REDIS_URL`
- `BETA_REDIS_HOST_PORT`

### Queue naming and isolation

- `PARSE_QUEUE_NAME`
- `PARSE_QUEUE_NAME_CLOUD`
- `PARSE_QUEUE_NAME_LOCAL`
- `PARSE_QUEUE_NAME_RULES`
- `BETA_PARSE_QUEUE_NAME`
- `BETA_PARSE_QUEUE_NAME_CLOUD`
- `BETA_PARSE_QUEUE_NAME_LOCAL`
- `BETA_PARSE_QUEUE_NAME_RULES`

### Retry / worker tuning

- `PARSE_QUEUE_MAX_RETRIES`
- `PARSE_QUEUE_MAX_RETRIES_CLOUD`
- `PARSE_QUEUE_MAX_RETRIES_LOCAL`
- `PARSE_QUEUE_MAX_RETRIES_RULES`
- `PARSE_QUEUE_CONCURRENCY_CLOUD`
- `PARSE_QUEUE_CONCURRENCY_LOCAL`
- `PARSE_QUEUE_CONCURRENCY_RULES`
- `PARSE_QUEUE_CLOUD_MIN_INTERVAL_SECONDS`
- `PARSE_QUEUE_CLAIM_TTL_SECONDS`
- `PARSE_QUEUE_SHUTDOWN_DRAIN_SECONDS`
- `PARSE_QUEUE_STALE_JOB_MINUTES`

### Job sync maintenance

- `JOB_SYNC_ENABLED`
- `JOB_SYNC_STALE_THRESHOLD_HOURS`
- `JOB_SYNC_SOFT_DELETE_MISSES`
- `JOB_SYNC_HARD_PURGE_DAYS`
- `JOB_SYNC_DISPATCH_INTERVAL_SECONDS`
- `JOB_SYNC_CLEANUP_INTERVAL_SECONDS`
- `JOB_SYNC_LOCK_TTL_SECONDS`
- `JOB_SYNC_CLEANUP_LOCK_TTL_SECONDS`
- `JOB_SYNC_CATEGORY_SCHEDULE_JSON`
- `JOB_SYNC_ENABLED_PROVIDERS_JSON`
- `JOB_LINK_BACKFILL_BATCH_SIZE`
- `JOB_LINK_BACKFILL_INTERVAL_SECONDS`
- `JOB_DEDUP_BACKFILL_BATCH_SIZE`
- `JOB_DEDUP_BACKFILL_INTERVAL_SECONDS`
- `JOB_COUNTRY_BACKFILL_BATCH_SIZE`
- `JOB_COUNTRY_BACKFILL_INTERVAL_SECONDS`
- `JOB_STALE_AUDIT_AGE_DAYS`
- `JOB_STALE_AUDIT_ESCALATION_DAYS`
- `JOB_STALE_MAX_UNCHANGED_DAYS`
- `JOB_STALE_AUDIT_BATCH_SIZE`
- `JOB_STALE_AUDIT_INTERVAL_SECONDS`
- `JOB_STALE_AUDIT_RECHECK_HOURS`

## Resume Parsing

### Cloud parsing

- `ZAI_API_KEY`
- `ZAI_OCR_URL`
- `ZAI_LLM_URL`
- `ZAI_LLM_MODEL`
- `ZAI_LLM_MAX_TOKENS`

### Local pipeline

- `USE_LOCAL_PIPELINE`
- `LOCAL_OCR_URL`
- `LOCAL_OCR_MODEL`
- `LOCAL_LLM_URL`
- `LOCAL_LLM_MODEL`
- `LOCAL_OCR_TIMEOUT`
- `LOCAL_LLM_TIMEOUT`
- `LOCAL_OCR_DPI`

## Beta-Specific Tunnel / Routing

- `DEV_DOMAIN`
- `CLOUDFLARE_BETA_TUNNEL_TOKEN`
- `CLOUDFLARED_IMAGE` (defaults in `docker-compose.beta.yml` match `env-examples/beta/.env.example`)
- `DEV_TLS_ENABLED`
- `DEV_TLS_CERT_PATH`
- `DEV_TLS_KEY_PATH`

Current beta deployments use the `cloudflared` tunnel override, so the tunnel token is part of the repo-managed beta shape.

## Compatibility / legacy keys (keep in templates; do not remove silently)

- `ADMIN_BOOTSTRAP_USERNAME` — present for older automation; credential login uses email-style bootstrap fields (see `backend/app/api/auth.py`).
- `DEV_AUTH_TEST_USERNAME` — legacy fallback; prefer `DEV_AUTH_TEST_EMAIL` for the seeded dev account.

## Operational Reminders

- `scripts/uah.sh` is the canonical lifecycle entrypoint.
- `scripts/lib/env-feature-check.sh` is the lifecycle-side env validation helper.
- `bash scripts/uah.sh <env> audit ...` is the canonical security audit entrypoint.
- Env templates should stay aligned with `backend/app/core/config.py` and the compose files.
