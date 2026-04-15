import GreenhouseAdapter from '../../ats/GreenhouseAdapter.js'

/**
 * Example Corp uses Greenhouse with a branded hosted board and a custom apply page
 * banner, so page detection needs one company-specific check before the base logic.
 */
export default class ExampleCorpGreenhouseAdapter extends GreenhouseAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    if (!parsedUrl) return false

    return parsedUrl.hostname === 'boards.greenhouse.io'
      && parsedUrl.pathname.startsWith('/examplecorp')
  }

  getCompanyName() {
    return 'Example Corp'
  }

  detectJobDetails() {
    const baseDetails = super.detectJobDetails()
    const title = this.queryText([
      '[data-company="examplecorp"] h1',
      '#header h1',
      'h1',
    ]) || baseDetails.title

    return {
      ...baseDetails,
      title: title || null,
      company: this.getCompanyName(),
    }
  }

  isApplicationPage() {
    if (Boolean(this.queryText(['.examplecorp-application-banner']))) {
      return true
    }

    return super.isApplicationPage()
  }

  getSupportLevel() {
    return 'partial'
  }
}
