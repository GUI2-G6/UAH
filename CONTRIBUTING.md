# Contributing To UAH

This guide covers the day-to-day contribution rules for the repository. For the detailed branch and PR flow, use [docs/WORKFLOW.md](docs/WORKFLOW.md).

## Before You Start

- Check the [issues board](https://github.com/GUI2-G6/UAH/issues) for existing work.
- Comment on the issue before starting so ownership is visible.
- If there is no issue yet, create one first.

## Branch Naming

All work should branch from `dev`.

| Type | Format | Example |
| --- | --- | --- |
| Feature | `feature/short-description` | `feature/gmail-oauth-status` |
| Bug fix | `fix/short-description` | `fix/status-page-auth-state` |
| Chore / infra | `chore/short-description` | `chore/update-env-sync-check` |
| Docs | `docs/short-description` | `docs/rewrite-backend-guide` |

Keep names lowercase and hyphenated.

## What To Update With Your Change

If your change affects any of these surfaces, update the matching docs in the same PR:

- backend behavior or required env vars
- frontend route or auth/runtime behavior
- browser extension build/runtime/autofill behavior
- operator-facing lifecycle or deployment behavior

Use [docs/README.md](docs/README.md) to find the current source-of-truth doc before you open the PR.

## Migrations And Backfills

- If a migration adds a derived field to `jobs`, ship an automated backfill path in the same change.
- Prefer the existing Celery maintenance-task pattern over one-off manual scripts.
- Do not destroy and recreate populated columns just to backfill them unless the migration explicitly requires destructive replacement.

## Pull Requests

- All changes to `dev` should go through a pull request.
- Use a clear PR title that describes the outcome.
- Link the issue with `Closes #XX` when appropriate.
- Fill out the PR template completely.
- If a change alters setup, behavior, or operator workflow, mention which docs you updated.

## Commit Style

Prefer clear, present-tense messages:

- `Add Gmail integration status endpoint`
- `Fix saved jobs pagination for authenticated users`
- `Rewrite beta setup docs for cloudflared tunnel flow`

Avoid vague messages like:

- `stuff`
- `fixed it`
- `wip`

## Environment And Secrets

- Never commit `.env` files.
- Runtime `.env` always belongs at the repository root for repo-managed workflows.
- If you suspect a secret was committed, notify the maintainers immediately.

### Keeping env templates aligned with the backend

Any new or removed environment variable read in `backend/app/core/config.py` must be reflected in **`env-examples/dev/.env.example`** and **`env-examples/beta/.env.example`** in the same pull request (with comments and placeholder values).

Before you push, run from the repo root:

```bash
npm run check:env
```

Or: `python .github/scripts/check_env_sync.py --all-templates` (add `--suggest` for placeholder stubs when something is missing).

Pull requests to `dev`, `beta`, and `prod` run the **ENV Example Sync Check** CI job; it fails if either template drifts from `config.py`.

Also update [`docs/SERVER_ENV_CHECKLIST.md`](docs/SERVER_ENV_CHECKLIST.md) when operators need to know about a new knob.

### Vite-only variables (`frontend/`, `landing/`)

Variables consumed as `import.meta.env.VITE_*` or `process.env.VITE_*` are not scanned by `check_env_sync.py`. When you add or rename one, update **`frontend/.env.local.example`**, **`landing/.env.local.example`**, and (for full-stack local) **`env-examples/local/.env.example`** as appropriate, and grep the codebase for usages so docs stay accurate.

## Questions

- Product / infra / workflow questions: comment on the issue or reach out to the project lead.
- For uncertainty about documentation placement, start with [docs/README.md](docs/README.md) instead of creating a new ad hoc doc.
