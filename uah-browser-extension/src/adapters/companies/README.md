# Company Overrides

Company overrides are the narrowest layer in the extension adapter system.

They exist because two employers using the same ATS can still ship different field labels, extra custom sections, or non-standard page structure.

## Rules

- Name files as `[CompanyName][ATS]Adapter.js`.
- Extend the relevant ATS adapter, never `BaseATSAdapter` directly.
- Keep the override minimal.
- Add a top-level doc comment explaining what the employer does differently.

## When To Create An Override

Create one when the difference is clearly employer-specific, such as:

- a custom work authorization section
- a differently labeled required field
- an employer-specific detail wrapper for job metadata

Do not create one when the improvement belongs in the shared ATS adapter.

## Minimal Pattern

```js
import WorkdayAdapter from '../../ats/WorkdayAdapter.js'

/**
 * Describe the company-specific deviation here.
 */
export default class AcmeCorpWorkdayAdapter extends WorkdayAdapter {
  matches(url) {
    return this.toUrl(url)?.hostname === 'acmecorp.wd1.myworkdayjobs.com'
  }

  getCompanyName() {
    return 'Acme Corp'
  }
}
```

## Review Heuristic

If an override starts growing large, stop and ask whether the shared platform adapter should learn a better generic selector or helper instead.

## Related Docs

- [../ADAPTERS.md](../ADAPTERS.md)
