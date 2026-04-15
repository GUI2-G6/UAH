# Server Environment Checklist

This checklist captures environment variables that must exist on server-side `.env` files for reliable UAH operations.

## Required For Startup

- `POSTGRES_PASSWORD`
- `SECRET_KEY`
- `SESSION_SECRET`

## Required For Core Auth and Search Features

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `MUSE_API_KEY`

## Dev Test Account Controls

Document these keys in env templates even when disabled:

- `DEV_AUTH_TEST_ACCOUNT_ENABLED`
- `DEV_AUTH_TEST_PASSWORD`
- `DEV_AUTH_TEST_EMAIL`
- `DEV_AUTH_TEST_USERNAME` (legacy fallback only)
- `DEV_AUTH_TEST_FIRST_NAME`
- `DEV_AUTH_TEST_LAST_NAME`
- `DEV_AUTH_TEST_IS_ADMIN`
- `DEV_AUTH_TEST_ROTATE_PASSWORD`

Environment policy:

- Dev/local: may enable test account; when enabled, email and password must be set.
- `DEV_AUTH_TEST_USERNAME` is legacy-only compatibility and should be an email value if used.
- Beta/prod: must keep `DEV_AUTH_TEST_ACCOUNT_ENABLED=false`.

## Required For Gmail Integration

- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REDIRECT_URI`

## Required For Beta Tunnel

- `CLOUDFLARE_BETA_TUNNEL_TOKEN` (beta only)

## Required When Queue Is Enabled

- `REDIS_ENABLED=true`
- `REDIS_URL=redis://uah-redis:6379/0` (dev default)
- `PARSE_QUEUE_NAME`
- `PARSE_QUEUE_NAME_CLOUD`
- `PARSE_QUEUE_NAME_LOCAL`
- `PARSE_QUEUE_NAME_RULES`
- `BETA_REDIS_URL=redis://uah-beta-redis:6379/0` (beta compose override default)
- `BETA_PARSE_QUEUE_NAME`
- `BETA_PARSE_QUEUE_NAME_CLOUD`
- `BETA_PARSE_QUEUE_NAME_LOCAL`
- `BETA_PARSE_QUEUE_NAME_RULES`
- `BETA_REDIS_HOST_PORT=6380` (when dev and beta run on the same host)

## Recommended Parse Queue Controls

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

## Optional Job Board URL Validation Controls

- `JOBS_URL_VALIDATION_ENABLED`
- `JOBS_URL_VALIDATION_TIMEOUT_SECONDS`
- `JOBS_URL_VALIDATION_MAX_CHECKS_PER_REQUEST`
- `JOBS_URL_VALIDATION_CONCURRENCY`
- `JOBS_URL_VALIDATION_BAD_TTL_SECONDS`
- `JOBS_URL_VALIDATION_GOOD_TTL_SECONDS`
- `JOBS_URL_VALIDATION_UNKNOWN_TTL_SECONDS`

## Required For Cloud Parse

- `ZAI_API_KEY`
- `ZAI_OCR_URL`
- `ZAI_LLM_URL`
- `ZAI_LLM_MODEL`
- `ZAI_LLM_MAX_TOKENS`

## Required When Local Pipeline Is Enabled

- `USE_LOCAL_PIPELINE=true`
- `LOCAL_OCR_URL`
- `LOCAL_OCR_MODEL`
- `LOCAL_LLM_URL`
- `LOCAL_LLM_MODEL`

## Operational Notes

- Runtime script entrypoint is `scripts/uah.sh`.
- `scripts/uah.sh` auto-detects environment context when env is omitted (path and root `.env` heuristics).
- Lifecycle env requirement check entrypoint is `scripts/lib/env-feature-check.sh`.
- Security audit entrypoint is `scripts/uah.sh <dev|beta|prod> audit`.
- Dev cert sync hook is `scripts/dev/certbot-sync-dev-cert.sh`.
- Password reset script reads `.env` from repo root by default and supports override via `UAH_ENV_FILE`.
- Concurrent dev and beta on one host require distinct Redis host ports (`REDIS_HOST_PORT=6379`, `BETA_REDIS_HOST_PORT=6380`).
- Beta queue defaults should use the `uah:beta:*` namespace to avoid cross-environment key overlap.
- `scripts/uah.sh` runs env checks during startup preflight and warns after sync operations.
- Debug operations are first-class under `scripts/uah.sh <env> debug ...` for connectivity, logs, queue, network, database, and dev user admin tasks.
