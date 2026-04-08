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
- [x] Add Local Ollama + Redis queue env block to env-examples/beta/.env.example
- [x] Add backend environment passthrough defaults for new vars in docker-compose.yml
- [x] Validate Phase 1 file changes

### Phase 2 - Configuration Surface
- [x] Add local pipeline settings to backend/app/core/config.py
- [x] Add Redis queue settings to backend/app/core/config.py
- [x] Keep ZAI settings unchanged and default feature flags off

### Phase 3 - Resume Parser Local Adapters
- [x] Add ocr_pdf_local(pdf_bytes) to backend/app/services/resume_parser.py
- [x] Add categorize_with_local_llm(md_text) to backend/app/services/resume_parser.py
- [x] Add ocr_pdf_dispatch(pdf_bytes)
- [x] Add categorize_dispatch(md_text)

### Phase 4 - API Dispatch Integration
- [x] Replace OCR call with ocr_pdf_dispatch in backend/app/api/resume.py
- [x] Replace LLM call with categorize_dispatch in backend/app/api/resume.py
- [x] Update imports for dispatch functions
- [x] Apply to sync parse and async parse worker paths

### Phase 5 - Redis Queue Service
- [x] Create backend/app/services/parse_queue.py
- [x] Create backend/app/services/parse_job_runner.py shared job runner
- [x] Add enqueue_parse_job(job_id, resume_id, user_id, method)
- [x] Add get_queue_depth()
- [x] Add get_job_redis_status(job_id)
- [x] Add start_queue_worker()
- [x] Add _process_job(job_data)
- [x] Add _worker_loop()
- [x] Add sequential processing and retry/backoff
- [x] Add Redis-unavailable fallback behavior

### Phase 6 - Startup and Endpoint Wiring
- [x] Start queue worker in backend/app/main.py lifespan when REDIS_ENABLED=true
- [x] Add resume async enqueue path with fallback in backend/app/api/resume.py
- [x] Add authenticated queue status endpoint in backend/app/api/resume.py

### Phase 7 - Verification
- [x] Verify docker compose syntax
- [x] Verify backend dependency and Dockerfile build assumptions
- [ ] Smoke test with feature flags off
- [ ] Smoke test local pipeline on
- [ ] Smoke test Redis queue on

### Phase 8 - Temporary Secure Desktop Routing
- [x] Add scoped temporary route apply script for desktop Ollama endpoint
- [x] Add scoped route verification script (host + backend container)
- [x] Add rollback script for route and NAT cleanup
- [x] Add docs runbook under docs/beta-prep for apply/verify/rollback flow
- [x] Execute apply/verify/rollback scripts on target VM
- [x] Validate end-to-end upload/parse with desktop endpoint and Redis enabled

### Phase 9 - Beta UX and Reliability Enhancements
- [x] Add explicit parse source support (cloud/local/rules) in backend parse flows
- [x] Preserve async queue processing with explicit parse source values
- [x] Remove duplicate resume PDF route handler in backend
- [x] Implement authenticated PDF preview loading in frontend modal
- [x] Add always-visible queue panel in Imported Resumes view
- [x] Add dev-only global queue scope toggle support in queue API + frontend
- [x] Add parse method badges for each resume row
- [x] Replace parse selector with Cloud AI / Local AI / Rules options
- [x] Add parse pipeline details popup card in frontend
- [x] Harden network helper scripts for read-only sysctl and backend /32 source scope
- [x] Remove requests dependency from connectivity helper script
- [x] Update routing runbook and beta env example notes for new behavior

## Change Log
- 2026-04-08: Created plan document and initial checklist.
- 2026-04-08: Added Redis service, healthcheck, and redis_data volume in docker-compose.yml.
- 2026-04-08: Added redis==5.0.1 to backend/requirements.txt.
- 2026-04-08: Added poppler-utils install layer to backend/Dockerfile.
- 2026-04-08: Added Local Ollama and Redis queue environment passthrough defaults to backend service in docker-compose.yml.
- 2026-04-08: Added Local Ollama and Redis queue feature-flag blocks to root .env.
- 2026-04-08: Added Local Ollama and Redis queue feature-flag blocks to env-examples/beta/.env.example.
- 2026-04-08: Validated Phase 1 file set (compose config rendered successfully; file-level diagnostics clean).
- 2026-04-08: Completed Phase 2 configuration settings in backend/app/core/config.py (local pipeline + Redis queue flags/settings; ZAI defaults unchanged).
- 2026-04-08: Completed Phase 3 parser adapters in backend/app/services/resume_parser.py (local OCR via pdftoppm + Ollama, local LLM parser, and feature-flag dispatch functions).
- 2026-04-08: Completed Phase 4 API dispatch integration in backend/app/api/resume.py (upload/parse paths and async job wrapper now route through dispatchers).
- 2026-04-08: Completed Phase 5 Redis queue service in backend/app/services/parse_queue.py with sequential worker loop, retry/backoff, and Redis-unavailable fallback behavior.
- 2026-04-08: Added backend/app/services/parse_job_runner.py to centralize parse execution logic for both BackgroundTasks and Redis worker processing.
- 2026-04-08: Completed Phase 6 wiring in backend/app/main.py and backend/app/api/resume.py (worker startup/shutdown, Redis enqueue branch, queue status endpoint).
- 2026-04-08: Marked Phase 7 static checks complete (compose renders, dependency/build assumptions validated from committed files).
- 2026-04-08: Added temporary secure desktop routing scripts under scripts/network (apply/check/rollback).
- 2026-04-08: Added docs/beta-prep/TEMP_DESKTOP_OLLAMA_ROUTING_RUNBOOK.md for operator run flow.
- 2026-04-08: Completed VM-side temporary route validation and confirmed backend reachability to desktop Ollama endpoint (10.8.0.8:11434).
- 2026-04-08: Added explicit cloud/local/rules parse source support across sync and async parse paths.
- 2026-04-08: Fixed PDF preview auth path by removing duplicate backend route and adding authenticated frontend PDF blob loading.
- 2026-04-08: Added always-visible queue panel with user position data and dev-only global queue scope.
- 2026-04-08: Expanded parse selection UI to Cloud AI / Local AI / Rules with pipeline details popup; added parse method tags to resume rows.
- 2026-04-08: Hardened network helper scripts (backend /32 source scope, read-only sysctl handling, stdlib connectivity check) and updated routing runbook.
