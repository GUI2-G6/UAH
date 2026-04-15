import WorkdayAdapter from '../../ats/WorkdayAdapter.js'

/**
 * Example Corp uses Workday but adds a custom work authorization section that the
 * base Workday selectors do not label consistently across every step.
 */
export default class ExampleCorpWorkdayAdapter extends WorkdayAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    return Boolean(parsedUrl && parsedUrl.hostname === 'examplecorp.wd1.myworkdayjobs.com')
  }

  getCompanyName() {
    return 'Example Corp'
  }

  detectFormFields() {
    const baseFields = super.detectFormFields()
    const workAuthorization = this.findFieldByLabel([
      'work authorization',
      'authorized to work',
      'sponsorship',
    ])

    if (!workAuthorization) {
      return baseFields
    }

    return {
      ...baseFields,
      workAuthorization,
    }
  }

  getSupportLevel() {
    return 'partial'
  }
}
