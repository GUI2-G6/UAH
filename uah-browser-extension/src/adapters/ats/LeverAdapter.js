import BaseATSAdapter from '../base/BaseATSAdapter.js'

function humanizeCompanySlug(slug) {
  return String(slug || '')
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
    || null
}

export default class LeverAdapter extends BaseATSAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    if (!parsedUrl || parsedUrl.hostname !== 'jobs.lever.co') {
      return false
    }

    const [company] = parsedUrl.pathname.split('/').filter(Boolean)
    return Boolean(company)
  }

  getATSName() {
    return 'Lever'
  }

  extractCompanySlug() {
    const parsedUrl = this.toUrl()
    if (!parsedUrl) return null
    return parsedUrl.pathname.split('/').filter(Boolean)[0] || null
  }

  detectJobDetails() {
    const baseDetails = super.detectJobDetails()
    const title = this.queryText([
      '.posting-headline h2',
      '.posting-headline h1',
      '.posting-headline',
      'h1',
    ]) || baseDetails.title
    const company = baseDetails.company || humanizeCompanySlug(this.extractCompanySlug())
    const location = this.queryText([
      '.posting-categories .location',
      '.location',
      '.posting-categories',
    ]) || baseDetails.location

    return {
      title: title || null,
      company: company || null,
      location: location || null,
    }
  }

  isApplicationPage() {
    if (super.isApplicationPage()) return true

    return Boolean(this.queryText([
      '.application-page',
      '.application-form',
      'form#application-form',
    ]))
  }
}
