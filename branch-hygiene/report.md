# Branch hygiene and security alignment

## Branch inventory and classification
- **dev** – keep public; canonical secure baseline; no changes required.
- **prod** – keep public; requires sync to dev security baseline (apply `branch-hygiene/prod-security.patch`).
- **copilot/cleanup-public-branch-hygiene** – working branch for this cleanup; keep until patch applied, then delete.
- **copilot/scrub-repo-for-security-concerns** – stale, insecure placeholders (`uah_dev_pass`, `change-me-in-production`, admin bypass env); recommend delete or make private.
- **copilot/scrub-repo-for-security-concerns-again** – stale, insecure placeholders; recommend delete or make private.
- **copilot/scrub-repo-for-security-concerns-another-one** – already aligned with dev baseline; can delete if unused to reduce surface.
- **copilot/review-oauth-integration-guide** – stale, insecure placeholders; recommend delete or make private.

## Required branch actions
1. **Prod hardening (must-do before release):**
   - Apply `branch-hygiene/prod-security.patch` onto `prod` to add the secure `.env.example`, require secrets in `docker-compose.yml`, and enforce secret validation in `backend/app/core/config.py` (matches `dev`).
   - Command: `git checkout prod && git apply branch-hygiene/prod-security.patch && git commit -m "Align prod security files to dev" && git push origin prod`.
2. **Stale copilot branches:** delete or restrict visibility for the three insecure branches listed above; default to no deletion if ownership is unclear.
3. **Protected branch:** no action on `dev` (do not rebase or rewrite).

## Pattern scan summary
- `uah_dev_pass` found on: origin/prod, copilot/scrub-repo-for-security-concerns*, copilot/review-oauth-integration-guide.
- `change-me-in-production` found on: copilot/scrub-repo-for-security-concerns*, copilot/review-oauth-integration-guide.
- No matches for these patterns on `dev` or `copilot/scrub-repo-for-security-concerns-another-one`.

## Release readiness
- **Go/No-Go:** **No-Go until prod is patched and stale insecure copilot branches are removed or made private.**
- **Blockers/permissions needed:** ability to push to `prod` and permission to delete/lock stale `copilot/*` branches.
