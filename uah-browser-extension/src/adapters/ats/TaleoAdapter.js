import BaseATSAdapter from '../base/BaseATSAdapter.js'

const TALEO_HOST_RE = /(?:^|\.)(taleo\.net|oraclecloud\.com)$/i

export default class TaleoAdapter extends BaseATSAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    if (!parsedUrl) return false
    if (TALEO_HOST_RE.test(parsedUrl.hostname)) return true
    return /\/careersection\//i.test(parsedUrl.pathname)
  }

  getATSName() {
    return 'Taleo'
  }

  detectJobDetails() {
    const baseDetails = super.detectJobDetails()
    const title = this.queryText([
      '#requisitionDescriptionInterface\\.ID1654\\.row1',
      '.titlepage',
      '.jobTitle',
      'h1',
    ]) || baseDetails.title
    const location = this.queryText([
      '.requisitionDescription li',
      '.jobLocation',
      '.location',
    ]) || baseDetails.location
    return {
      title: title || null,
      company: baseDetails.company || null,
      location: location || null,
    }
  }

  isApplicationPage() {
    if (super.isApplicationPage()) return true
    return Boolean(this.queryText([
      'button[id*="apply"]',
      'a[id*="apply"]',
      '.apply',
      '#apply',
    ]))
  }
}
