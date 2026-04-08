# UAH Resume Pipeline Migration Plan

## Goal
Migrate resume OCR and parsing from ZAI cloud APIs to a feature-flagged local Ollama pipeline, and introduce an optional Redis-backed parse queue with safe fallback behavior.

## Status Key
- [ ] Not started
- [x] Completed

## Phase Checklist

### Phase 1 - Infrastructure Prerequisites
- [x] Add Redis service to docker-compose.yml (service, healthcheck, persistent volume)
- [x] Add Redis dependency to backend/requirements.txt
- [x] Install poppler-utils in backend/Dockerfile for pdftoppm
- [x] Add Local Ollama + Redis queue env block to root .env
- [x] Add Local Ollama + Redis queue env block to docs/beta-prep/.env.beta.example
- [x] Add backend environment passthrough defaults for new vars in docker-compose.yml
- [x] Validate Phase 1 file changes

### Phase 2 - Configuration Surface
- [x] Add local pipeline settings to backend/app/core/config.py
- [x] Add Redis queue settings to backend/app/core/config.py
- [x] Keep ZAI settings unchanged and default feature flags off

### Phase 3 - Resume Parser Local Adapters
- [ ] Add ocr_pdf_local(pdf_bytes) to backend/app/services/resume_parser.py
- [ ] Add categorize_with_local_llm(md_text) to backend/app/services/resume_parser.py
- [ ] Add ocr_pdf_dispatch(pdf_bytes)
- [ ] Add categorize_dispatch(md_text)

### Phase 4 - API Dispatch Integration
- [ ] Replace OCR call with ocr_pdf_dispatch in backend/app/api/resume.py
- [ ] Replace LLM call with categorize_dispatch in backend/app/api/resume.py
- [ ] Update imports for dispatch functions
- [ ] Apply to sync parse and async parse worker paths

### Phase 5 - Redis Queue Service
- [ ] Create backend/app/services/parse_queue.py
- [ ] Add enqueue_parse_job(job_id, resume_id, user_id, method)
- [ ] Add get_queue_depth()
- [ ] Add get_job_redis_status(job_id)
- [ ] Add start_queue_worker()
- [ ] Add _process_job(job_data)
- [ ] Add _worker_loop()
- [ ] Add sequential processing and retry/backoff
- [ ] Add Redis-unavailable fallback behavior

### Phase 6 - Startup and Endpoint Wiring
- [ ] Start queue worker in backend/app/main.py lifespan when REDIS_ENABLED=true
- [ ] Add resume async enqueue path with fallback in backend/app/api/resume.py
- [ ] Add authenticated queue status endpoint in backend/app/api/resume.py

### Phase 7 - Verification
- [ ] Verify docker compose syntax
- [ ] Verify backend dependency and Dockerfile build assumptions
- [ ] Smoke test with feature flags off
- [ ] Smoke test local pipeline on
- [ ] Smoke test Redis queue on

## Change Log
- 2026-04-08: Created plan document and initial checklist.
- 2026-04-08: Added Redis service, healthcheck, and redis_data volume in docker-compose.yml.
- 2026-04-08: Added redis==5.0.1 to backend/requirements.txt.
- 2026-04-08: Added poppler-utils install layer to backend/Dockerfile.
- 2026-04-08: Added Local Ollama and Redis queue environment passthrough defaults to backend service in docker-compose.yml.
- 2026-04-08: Added Local Ollama and Redis queue feature-flag blocks to root .env.
- 2026-04-08: Added Local Ollama and Redis queue feature-flag blocks to docs/beta-prep/.env.beta.example.
- 2026-04-08: Validated Phase 1 file set (compose config rendered successfully; file-level diagnostics clean).
- 2026-04-08: Completed Phase 2 configuration settings in backend/app/core/config.py (local pipeline + Redis queue flags/settings; ZAI defaults unchanged).
