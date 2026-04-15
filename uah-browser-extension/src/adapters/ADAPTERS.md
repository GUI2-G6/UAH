# ATS Adapter System

This document describes the current adapter contract used by the browser extension.

Use it together with:

- [../../README.md](../../README.md)
- [companies/README.md](companies/README.md)

## Resolution Order

Adapter lookup is intentionally two-stage:

1. company-specific overrides
2. base ATS adapters

That precedence matters. A company override should always win before the extension falls back to the generic platform adapter.

## Base Contract

Every registered adapter must implement:

- `matches(url)`
- `getATSName()`
- `getCompanyName()`
- `detectJobDetails()`
- `detectFormFields()`
- `isApplicationPage()`
- `getSupportLevel()`

`getCompanyName()` returning a non-empty value is what makes an adapter a company override instead of a base ATS adapter.

## Base ATS Adapters

Current base platforms:

- Workday
- Greenhouse
- Lever
- iCIMS

Base adapters should handle platform-wide selectors and fallbacks that are likely to help more than one employer instance.

## Company Overrides

Company overrides are appropriate when one employer's implementation diverges from the platform defaults in a way that is not broadly reusable.

Good override candidates:

- renamed or badly labeled custom fields
- extra required sections unique to one employer
- job details moved into employer-specific wrappers

Bad override candidates:

- selector improvements that would help most or all sites on the same ATS

## Support Levels

- `base`: platform recognition plus shared fallback behavior
- `partial`: meaningful employer-specific tailoring, but manual review still expected
- `full`: intentionally tuned end-to-end support with strong evidence and repeatable coverage

Reserve `full` for genuinely mature coverage.

## How To Add A New ATS Platform

1. Create a new adapter in `src/adapters/ats/`.
2. Extend `BaseATSAdapter`.
3. Reuse shared helpers where possible.
4. Register the adapter in `src/adapters/index.js`.
5. Add tests for positive and negative URL matches.

## How To Add A Company Override

1. Identify the underlying ATS first.
2. Create the file in `src/adapters/companies/<ats-name>/`.
3. Extend the platform adapter, not `BaseATSAdapter` directly.
4. Override only the behavior that actually differs.
5. Register the override in `src/adapters/index.js`.
6. Add tests proving the override wins before the base ATS adapter.

## Testing Guidance

- test `matches()` with real-world positive and negative URLs
- test registry precedence for override-vs-base behavior
- test custom field discovery when the override exists only for one employer deviation
- stop before final application submission when manually checking live pages

## Related Docs

- [companies/README.md](companies/README.md)
- [../../README.md](../../README.md)
