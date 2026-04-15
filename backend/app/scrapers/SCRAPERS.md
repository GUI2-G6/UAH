# UAH Scraper System

This directory is a forward-looking scaffold for ethical scraper adapters. It does not replace the current live provider system in `backend/app/providers/`, and it is not wired into Celery yet. Its job is to make future provider additions consistent, reviewable, and safe before we plug anything into the live job-sync pipeline.

## Architecture Overview

```text
PreScrapingChecklist.py
        |
        v
 provider approval
        |
        v
BaseProviderAdapter
        |
        +--> provider adapters (scaffold)
        |
        +--> opt_out.py <--> opt_out_registry.json
        |
        v
registry.py
        |
        v
future pipeline integration
  (live app.providers / Celery wiring later)
```

- `checklist/PreScrapingChecklist.py` automates the first review pass for a new provider.
- `base/BaseProviderAdapter.py` defines the adapter contract, UAHBot user agent, robots handling, and request pacing.
- `providers/` contains scaffold-native adapters only. Current live examples remain in `backend/app/providers/`.
- `registry.py` resolves scaffold adapters for future integration work.
- `opt_out.py` and `opt_out_registry.json` provide a permanent, version-controlled removal path for providers.

## UAH Scraping Ethics

- We only scrape sites with no explicit robots.txt prohibition and no ToS language against automated access
- We identify ourselves as UAHBot/1.0 on every request
- We honor Crawl-delay directives
- We cache aggressively and never re-fetch unnecessarily
- We provide a clear opt-out mechanism — any provider can email data@uahapp.com to be removed, and we honor it without question
- We are not-for-profit — no individual profits from this data pipeline

## How To Add A New Provider

1. Run `python -m backend.app.scrapers.checklist.PreScrapingChecklist --url https://example.com`.
2. Review the output. The provider must be `APPROVED` before adapter work proceeds.
3. Create a new adapter in `backend/app/scrapers/providers/`.
4. Extend `BaseProviderAdapter` and implement every required method.
5. Register the adapter in `backend/app/scrapers/registry.py`.
6. Summarize the checklist outcome in the PR or documentation notes. Raw JSON logs remain local tooling artifacts because `checklist_log/` is gitignored.

## Opt-Out System

Providers can email `data@uahapp.com` from their organization domain to request removal. Requests are honored promptly, without debate, and permanently recorded in `opt_out_registry.json`.

Use the helper functions in `opt_out.py`:

- `register_opt_out(provider_name, base_url, contact_email, date, notes)`
- `check_opt_out(base_url)`
- `list_opted_out()`
- `remove_opt_out(base_url, confirmation_notes)`

The registry is committed to git on purpose. Opt-out requests should stay historically visible, auditable, and hard to accidentally erase.

## Rate Limiting Rules

- The base adapter default is `2.0` seconds between requests.
- The effective floor is always `1.0` seconds, even if a provider-specific override returns less.
- When `robots.txt` defines `Crawl-delay`, UAH uses the higher value between the adapter delay and the robots directive.
- Future providers should route all outbound HTTP calls through the base adapter request helper so the same pacing logic is applied everywhere.

## Normalization Schema

All adapters normalize into `app.schemas.job.NormalizedJob`.

| Field | Type |
| --- | --- |
| `provider` | `str` |
| `provider_job_id` | `str` |
| `provider_url` | `str \| None` |
| `apply_url` | `str \| None` |
| `apply_host` | `str \| None` |
| `apply_portal` | `str \| None` |
| `source_tags` | `list[str]` |
| `title` | `str` |
| `company` | `str \| None` |
| `company_url` | `str \| None` |
| `location` | `str \| None` |
| `is_remote` | `bool` |
| `job_type` | `str \| None` |
| `experience_level` | `str \| None` |
| `categories` | `list[str]` |
| `description` | `str \| None` |
| `published_at` | `datetime \| None` |

## Example Implementations

This scaffold intentionally does not duplicate the six live provider adapters that already exist in `backend/app/providers/`. Use these files as real normalization and request-shape examples:

- `backend/app/providers/the_muse.py`
- `backend/app/providers/arbeitnow.py`
- `backend/app/providers/findwork.py`
- `backend/app/providers/jooble.py`
- `backend/app/providers/adzuna.py`
- `backend/app/providers/careerjet.py`

## Provider Status

| Provider | Base URL | Rate Limit | Status | Checklist Review Date |
| --- | --- | --- | --- | --- |
| The Muse | `https://www.themuse.com` | `1000 req/hour` default | Active | Legacy / pending rerun |
| Arbeitnow | `https://www.arbeitnow.com` | `3.0s/request` default | Active | Legacy / pending rerun |
| Findwork | `https://findwork.dev` | `6.0s/request` default | Dormant | Legacy / pending rerun |
| Jooble | `https://jooble.org` | `1.5s/request` default | Dormant | Legacy / pending rerun |
| Adzuna | `https://www.adzuna.co.uk` | `1500 req/hour` plus `200/day` default budget | Dormant | Legacy / pending rerun |
| Careerjet | `https://www.careerjet.com` | Disabled stub | Dormant | Legacy / pending rerun |
| WhatJobs | `https://www.whatjobs.com` | `2.0s/request` scaffold default | Inactive | Pending |

## Opt-Out Contact

If you operate one of these sites and want UAH to stop indexing your content, email `data@uahapp.com` from your organization domain. Removal requests are honored promptly and permanently recorded.

## Contributing A New Adapter

- A merged PR is required before an adapter can be treated as part of the community-supported listing.
- Reaching out to an LTS team member before starting a new adapter is encouraged so contributors do not duplicate work.
- The pre-scraping checklist must pass before adapter work proceeds.
- Include a short checklist summary in the PR so reviewers can confirm why the provider was approved.
