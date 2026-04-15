import BaseATSAdapter from '../base/BaseATSAdapter.js'

const WORKDAY_HOST_RE = /^[a-z0-9-]+(?:\.wd\d+)?\.myworkdayjobs\.com$/i

function humanizeCompanySlug(slug) {
  return String(slug || '')
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
    || null
}

export default class WorkdayAdapter extends BaseATSAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    return Boolean(parsedUrl && WORKDAY_HOST_RE.test(parsedUrl.hostname))
  }

  getATSName() {
    return 'Workday'
  }

  extractCompanySlug() {
    const parsedUrl = this.toUrl()
    if (!parsedUrl) return null
    return parsedUrl.hostname.split('.')[0] || null
  }

  detectJobDetails() {
    const baseDetails = super.detectJobDetails()
    const title = this.queryText([
      '[data-automation-id="jobPostingHeader"]',
      '[data-automation-id="jobTitle"]',
      'h1',
    ]) || baseDetails.title
    const company = baseDetails.company || humanizeCompanySlug(this.extractCompanySlug())
    const location = this.queryText([
      '[data-automation-id="locations"]',
      '[data-automation-id="locationsList"]',
      '.css-129m7dg',
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
      '[data-automation-id="applyButton"]',
      '[data-automation-id="jobApplication"]',
    ]))
  }
}
