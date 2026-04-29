import BaseATSAdapter from '../base/BaseATSAdapter.js'

const DYNAMICS_HOST_RE = /(?:^|\.)(dynamics\.com|dynamics365\.com)$/i
const LEGACY_JOBSEARCH_PATH_RE = /\/pages\/jobsearch\.aspx$/i
const DYNAMICS_PATH_HINT_RE = /\b(candidate|apply|talent)\b/i

export default class DynamicsAdapter extends BaseATSAdapter {
  matches(url) {
    const parsedUrl = this.toUrl(url)
    if (!parsedUrl) return false

    if (DYNAMICS_HOST_RE.test(parsedUrl.hostname)) {
      return true
    }

    if (LEGACY_JOBSEARCH_PATH_RE.test(parsedUrl.pathname) && parsedUrl.searchParams.has('clientId')) {
      return true
    }

    return /(?:^|\.)(microsoftcrmportals\.com|powerappsportals\.com)$/i.test(parsedUrl.hostname)
      && DYNAMICS_PATH_HINT_RE.test(parsedUrl.pathname)
  }

  getATSName() {
    return 'Dynamics'
  }

  getSupportLevel() {
    return 'base'
  }
}
