import BaseATSAdapter from '../base/BaseATSAdapter.js'

const GREENHOUSE_SUBDOMAIN_RE = /^[a-z0-9-]+\.greenhouse\.io$/i

function humanizeCompanySlug(slug) {
  return String(slug || '')
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
    || null
}

export default class GreenhouseAdapter extends BaseATSAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    if (!parsedUrl) return false

    if (GREENHOUSE_SUBDOMAIN_RE.test(parsedUrl.hostname)) {
      return true
    }

    if (parsedUrl.hostname !== 'boards.greenhouse.io') {
      return false
    }

    const [company] = parsedUrl.pathname.split('/').filter(Boolean)
    return Boolean(company)
  }

  getATSName() {
    return 'Greenhouse'
  }

  extractCompanySlug() {
    const parsedUrl = this.toUrl()
    if (!parsedUrl) return null

    if (parsedUrl.hostname === 'boards.greenhouse.io') {
      return parsedUrl.pathname.split('/').filter(Boolean)[0] || null
    }

    return parsedUrl.hostname.split('.')[0] || null
  }

  detectJobDetails() {
    const baseDetails = super.detectJobDetails()
    const title = this.queryText([
      '[data-testid="job-name"]',
      '#header h1',
      '.app-title',
      'h1',
    ]) || baseDetails.title
    const company = baseDetails.company || humanizeCompanySlug(this.extractCompanySlug())
    const location = this.queryText([
      '#header .location',
      '.location',
      '[data-testid="job-location"]',
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
      '#application',
      '.application',
      '[data-qa="application-form"]',
    ]))
  }
}
