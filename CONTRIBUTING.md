# Contributing to UAH

Thanks for being part of the project. This guide covers how we work together so things stay organized as the codebase grows.

## Before You Start

- Check the [issues board](https://github.com/GUI2-G6/UAH/issues) for open work
- Comment on an issue before starting — this signals to the team that you're working on it and prevents duplicate effort
- If something you want to work on doesn't have an issue yet, create one first and assign yourself

## Branch Naming

All work happens on branches off `dev`. Use this format:

| Type | Format | Example |
|---|---|---|
| New feature | `feature/short-description` | `feature/gmail-oauth-scope` |
| Bug fix | `fix/short-description` | `fix/pdf-viewer-auth` |
| Chore/infra | `chore/short-description` | `chore/update-dependencies` |
| Documentation | `docs/short-description` | `docs/beta-setup-guide` |

Keep branch names lowercase and hyphenated. No spaces, no uppercase.

## Making Changes

1. Branch off `dev` — never branch off `prod` or `beta`
2. Make your changes in focused, logical commits
3. Write commit messages that describe what changed and why, not just "fix stuff"
4. Test your changes locally before opening a PR

## Pull Requests

- For the full branch and PR workflow, see [WORKFLOW.md](WORKFLOW.md).
- All changes to `dev` must come through a pull request — no direct pushes
- Title your PR clearly: what does it do?
- Reference the issue it closes using `Closes #XX` in the PR description
- Use the PR template — fill it out completely
- At least one team member should review before merging
- Do not merge your own PR without a review unless it is a critical hotfix and you have confirmed with @TrentBrownUML

## Commit Style

Use clear, present-tense commit messages:
- `Add Gmail OAuth scope endpoint`
- `Fix PDF viewer auth header not being passed`
- `Update CORS origins for beta environment`

Not:
- `stuff`
- `fixed it`
- `wip`

## Environment and Secrets

- Never commit `.env` files — they are gitignored, keep it that way
- If you add a new environment variable, add it to `env-examples/dev/.env.example` with a description and a safe placeholder value
- Runtime `.env` must live at the repository root when running the app/compose (do not run from files inside `env-examples/`)
- If you accidentally commit a secret, notify @TrentBrownUML immediately

## Questions

Reach out on Discord or comment on the relevant GitHub issue. @TrentBrownUML handles PM and infra questions.
