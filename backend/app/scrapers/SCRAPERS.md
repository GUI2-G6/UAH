# Scraper Scaffold

This directory documents the ethical scraper scaffold under `backend/app/scrapers/`.

Important boundary:

- this scaffold is not the same thing as the live provider pipeline in `backend/app/providers/`
- it exists to make future provider evaluation and adapter work more structured

## Current Role

The scaffold is for:

- provider review workflows
- opt-out bookkeeping
- a future adapter contract for scraper-based providers

It is not currently the primary runtime path for the live jobs catalog.

## Main Pieces

| File / area | Purpose |
| --- | --- |
| `checklist/PreScrapingChecklist.py` | First-pass provider review automation |
| `base/BaseProviderAdapter.py` | Shared adapter contract and request etiquette |
| `providers/` | Scaffold-native provider adapters |
| `registry.py` | Future scaffold adapter lookup |
| `opt_out.py` and `opt_out_registry.json` | Version-controlled provider removal path |

## Ethics And Guardrails

- honor `robots.txt`
- review provider terms before adapter work
- use clear identification and respectful pacing
- keep an explicit opt-out path
- preserve historical opt-out records in version control

## Live Pipeline Reminder

If you need the currently active provider implementations, use:

- `backend/app/providers/the_muse.py`
- `backend/app/providers/arbeitnow.py`
- `backend/app/providers/findwork.py`
- `backend/app/providers/jooble.py`
- `backend/app/providers/adzuna.py`
- `backend/app/providers/careerjet.py`

## Provider Status Table

The status table below is a planning aid, not a live-service guarantee.

`Legacy / pending rerun` means the last documented checklist review is no longer assumed current and should be rerun before treating the provider as newly approved.

| Provider | Base URL | Rate Limit | Status | Checklist Review Date |
| --- | --- | --- | --- | --- |
| The Muse | `https://www.themuse.com` | `1000 req/hour` default | Active | Legacy / pending rerun |
| Arbeitnow | `https://www.arbeitnow.com` | `3.0s/request` default | Active | Legacy / pending rerun |
| Findwork | `https://findwork.dev` | `6.0s/request` default | Dormant | Legacy / pending rerun |
| Jooble | `https://jooble.org` | `1.5s/request` default | Dormant | Legacy / pending rerun |
| Adzuna | `https://www.adzuna.co.uk` | `1500 req/hour` plus `200/day` default budget | Dormant | Legacy / pending rerun |
| Careerjet | `https://www.careerjet.com` | Disabled stub | Dormant | Legacy / pending rerun |
| Dummy Provider | `https://example.com` | `2.0s/request` scaffold default | Inactive | Pending |

## Adding A New Provider

1. Run the checklist.
2. Review robots/ToS/output manually.
3. Decide whether the provider belongs in the live pipeline now, the scaffold only, or not at all.
4. Capture the reasoning in the PR or current docs.

## Related Docs

- [../../../docs/provider-checklist-template.md](../../../docs/provider-checklist-template.md)
- [../../../docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md)
