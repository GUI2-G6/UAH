# Contributing To UAH

This guide covers the day-to-day contribution rules for the repository. For the detailed branch and PR flow, use [docs/WORKFLOW.MD](docs/WORKFLOW.MD).

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
- If you add a new env var, update the relevant `env-examples/*/.env.example` files.
- Runtime `.env` always belongs at the repository root for repo-managed workflows.
- If you suspect a secret was committed, notify the maintainers immediately.

## Questions

- Product / infra / workflow questions: comment on the issue or reach out to the project lead.
- For uncertainty about documentation placement, start with [docs/README.md](docs/README.md) instead of creating a new ad hoc doc.
