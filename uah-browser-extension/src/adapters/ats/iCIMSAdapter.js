import BaseATSAdapter from '../base/BaseATSAdapter.js'

function humanizeCompanySlug(slug) {
  return String(slug || '')
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
    || null
}

export default class ICIMSAdapter extends BaseATSAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    if (!parsedUrl || !parsedUrl.hostname.endsWith('.icims.com')) {
      return false
    }

    const labels = parsedUrl.hostname.split('.')
    return labels.length === 3 || (labels.length === 4 && labels[0] === 'careers')
  }

  getATSName() {
    return 'iCIMS'
  }

  extractCompanySlug() {
    const parsedUrl = this.toUrl()
    if (!parsedUrl) return null

    const labels = parsedUrl.hostname.split('.')
    if (labels.length === 4 && labels[0] === 'careers') {
      return labels[1] || null
    }

    return labels[0] || null
  }

  detectJobDetails() {
    const baseDetails = super.detectJobDetails()
    const title = this.queryText([
      '.iCIMS_Header .iCIMS_Header_Text',
      '.iCIMS_JobHeader h1',
      '.jobtitle',
      'h1',
    ]) || baseDetails.title
    const company = baseDetails.company || humanizeCompanySlug(this.extractCompanySlug())
    const location = this.queryText([
      '.iCIMS_JobHeader .iCIMS_JobHeaderField',
      '.iCIMS_JobContent .location',
      '.location',
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
      '.iCIMS_ApplyOnlineContainer',
      '.iCIMS_ApplyButton',
      'form[name="icimsapply"]',
    ]))
  }
}
