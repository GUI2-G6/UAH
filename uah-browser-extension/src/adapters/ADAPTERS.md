# ATS Adapter System

This scaffold introduces an extensible adapter layer for ATS-specific and company-specific job application assistance in `uah-browser-extension`.

## Architecture Overview

The registry resolves adapters in two stages:

1. Company-specific overrides
2. Base ATS adapters

If no company override matches the current page URL, the registry falls back to the generic adapter for that ATS platform.

```text
resolveAdapter(url)
  |
  +-- companyOverrides[]
  |     |
  |     +-- ExampleCorpWorkdayAdapter
  |     +-- ExampleCorpGreenhouseAdapter
  |
  +-- baseAdapters[]
        |
        +-- WorkdayAdapter
        +-- GreenhouseAdapter
        +-- LeverAdapter
        +-- iCIMSAdapter
```

## How To Add A New ATS Platform

1. Create a new file in `src/adapters/ats/`.
2. Extend `BaseATSAdapter`.
3. Implement every required public method:
   `matches(url)`, `getATSName()`, `getCompanyName()`, `detectJobDetails()`, `detectFormFields()`, `isApplicationPage()`, and `getSupportLevel()`.
4. Reuse the generic helpers where possible, especially `super.detectFormFields()`.
5. Register the adapter in `src/adapters/index.js`.
6. Add unit tests for `matches()` with real platform URL examples and nearby negative cases.

## How To Add A Company-Specific Override

1. Identify the underlying ATS platform first.
2. Create a file in `src/adapters/companies/[ats-name]/[CompanyName][ATS]Adapter.js`.
3. Extend the base ATS adapter for that platform, not `BaseATSAdapter` directly.
4. Add a top-level JSDoc comment describing what is different about this employer's instance.
5. Override only the methods that actually differ from the base adapter.
6. Register the override in `src/adapters/index.js`.
7. Add tests that prove the override wins over the base ATS adapter for that company's URL.

## URL Pattern Reference

| ATS | Supported pattern | Example |
| --- | --- | --- |
| Workday | `[company].wd1.myworkdayjobs.com` | `https://examplecorp.wd1.myworkdayjobs.com/en-US/careers/job/123` |
| Workday | `[company].wd3.myworkdayjobs.com` | `https://contoso.wd3.myworkdayjobs.com/en-US/jobs` |
| Workday | `[company].wd5.myworkdayjobs.com` | `https://fabrikam.wd5.myworkdayjobs.com/en-US/apply` |
| Workday | `[company].myworkdayjobs.com` | `https://northwind.myworkdayjobs.com/en-US/careers` |
| Greenhouse | `boards.greenhouse.io/[company]` | `https://boards.greenhouse.io/examplecorp/jobs/12345` |
| Greenhouse | `[company].greenhouse.io` | `https://examplecorp.greenhouse.io/jobs/12345` |
| Lever | `jobs.lever.co/[company]` | `https://jobs.lever.co/examplecorp/abc123` |
| iCIMS | `careers.[company].icims.com` | `https://careers.examplecorp.icims.com/jobs/1234/software-engineer/job` |
| iCIMS | `[company].icims.com` | `https://examplecorp.icims.com/jobs/1234/job` |

## Support Levels

- `base`: The adapter recognizes the ATS and provides the shared fallback behavior for that platform.
- `partial`: The adapter understands important customizations for one company, but contributors should still assume manual review is needed.
- `full`: The adapter is intentionally tuned for the target site end to end and should only be used when the implementation really covers the full application flow.

Contributors should start at `base`, upgrade to `partial` when handling known deviations, and reserve `full` for adapters with strong evidence and repeatable test coverage.

## Testing Guidance

- Start with unit tests for `matches()`, `resolveAdapter()`, and any custom selector behavior.
- When manually checking a real ATS URL, use a non-production or low-risk listing when possible.
- Stop before the final submission step. The goal is to confirm detection, field discovery, and step recognition, not to submit an application.
- Prefer read-only inspection in DevTools or the extension test harness over live form submission.

## Contributing

- A merged PR is required before an adapter can be treated as part of the community-supported listing.
- Reaching out to an LTS team member before starting a new adapter is encouraged so contributors do not duplicate work.
- If the change is really a shared selector improvement, prefer updating the base ATS adapter instead of creating a company override.
