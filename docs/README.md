# UAH Documentation Map

This directory is the documentation landing page for the repository.

Use it to answer two questions quickly:

1. Which document is the current source of truth?
2. Which documents are preserved only for historical context?

## Start Here

| Need | Current doc |
| --- | --- |
| Repo overview, local development, and stack entrypoints | [../README.md](../README.md) |
| System architecture and subsystem boundaries | [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) |
| Text-only architecture diagram for writeups/forms | [architecture/ARCHITECTURE_TEXT_DIAGRAM.md](architecture/ARCHITECTURE_TEXT_DIAGRAM.md) |
| Backend local development and runtime notes | [backend/README.md](backend/README.md) |
| Frontend local development and active UI/runtime behavior | [frontend/README.md](frontend/README.md) |
| Theme tokens, appearance modes, and theme-pack roadmap | [../shared/theme/README.md](../shared/theme/README.md) |
| Public landing SPA (build, deploy, tunnel notes) | [landing/README.md](landing/README.md) |
| Browser extension architecture, build, and testing | [../uah-browser-extension/README.md](../uah-browser-extension/README.md) |
| Browser extension build/repack/install in Chrome | [extension/BROWSER_EXTENSION_CHROME_INSTALL.md](extension/BROWSER_EXTENSION_CHROME_INSTALL.md) |
| Environment templates and runtime `.env` rules | [env-examples/README.md](env-examples/README.md) |
| Server-side env requirements and operational checklist | [SERVER_ENV_CHECKLIST.md](SERVER_ENV_CHECKLIST.md) |
| Contribution policy | [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| Branch / PR workflow | [WORKFLOW.md](WORKFLOW.md) |
| Security policy | [../SECURITY.md](../SECURITY.md) |
| Security audit script usage | [SECURITY_AUDIT_GUIDE.md](SECURITY_AUDIT_GUIDE.md) |
| Beta deployment setup | [beta-prep/BETA_SETUP.md](beta-prep/BETA_SETUP.md) |
| Beta release checklist | [beta-prep/SECURITY_CHECKLIST.md](beta-prep/SECURITY_CHECKLIST.md) |
| Cloudflare tunnel and access posture for beta | [beta-prep/CLOUDFLARE_SECURITY.md](beta-prep/CLOUDFLARE_SECURITY.md) |
| Temporary desktop Ollama route runbook | [beta-prep/TEMP_DESKTOP_OLLAMA_ROUTING_RUNBOOK.md](beta-prep/TEMP_DESKTOP_OLLAMA_ROUTING_RUNBOOK.md) |

## Subsystem Docs

These docs live next to the subsystem they describe because they are only useful when working in that area.

| Area | Doc | Notes |
| --- | --- | --- |
| Extension install guides and sync with `landing/public/docs` | [extension/README.md](extension/README.md) | Index for Chrome install doc; static copies require manual sync. |
| Extension ATS adapter system | [../uah-browser-extension/src/adapters/ADAPTERS.md](../uah-browser-extension/src/adapters/ADAPTERS.md) | Base ATS adapters, company overrides, and test expectations. |
| Extension company override rules | [../uah-browser-extension/src/adapters/companies/README.md](../uah-browser-extension/src/adapters/companies/README.md) | Narrow guide for company-specific adapter deviations. |
| Scraper scaffold | [../backend/app/scrapers/SCRAPERS.md](../backend/app/scrapers/SCRAPERS.md) | Forward-looking scaffold, not the live provider pipeline. |
| Provider review template | [provider-checklist-template.md](provider-checklist-template.md) | Checklist for evaluating new providers before adapter work. |

## Active Docs Rules

When editing the codebase, treat these conventions as repository policy:

- Root-level READMEs and docs in this directory should describe current behavior, not planned behavior.
- If a behavior is temporary, say that explicitly and name the current workaround.
- If a compatibility surface still exists, document it as compatibility-only instead of implying it is preferred.
- Prefer cross-links over duplicating the same explanation in multiple places.
- Put dated implementation notes, audits, and migration plans in [archive/](archive/README.md) instead of leaving them mixed with active guides.

## Historical Material

Historical docs are intentionally preserved, but they are no longer treated as the current source of truth.

- Historical audits, implementation notes, and migration plans live under [archive/](archive/README.md).
- Active guides should link to historical docs only when the old context still helps explain why something exists.
- If you are unsure whether a document is current, use the tables above first and treat archive docs as background only.
