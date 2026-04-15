# Company Overrides

Company overrides exist because ATS platforms are only partly standardized. Two employers can both use Workday, Greenhouse, Lever, or iCIMS and still ship meaningfully different application steps, labels, validation rules, and custom sections.

## Rules

- Name override files as `[CompanyName][ATS]Adapter.js`.
- Always extend the relevant base ATS adapter, never `BaseATSAdapter` directly.
- Keep overrides minimal. Only replace the methods that differ from the shared ATS behavior.

## How To Spot A Real Deviation

- Compare the target company's page structure against the base ATS adapter selectors.
- Look for extra required sections, renamed labels, non-standard apply-step banners, or job detail elements moved into custom wrappers.
- Confirm that the difference is company-specific and not a reusable improvement that belongs in the base ATS adapter.

## Minimal Override Pattern

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

  detectFormFields() {
    const baseFields = super.detectFormFields()
    const customField = this.findFieldByLabel(['work authorization'])
    return customField
      ? { ...baseFields, workAuthorization: customField }
      : baseFields
  }
}
```

When an override grows large, pause and check whether the base ATS adapter should learn a new shared selector instead.
