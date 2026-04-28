/**
 * Turn FastAPI and fetch failures into a single user-facing string.
 * Handles guardrails (429), validation (400/422), and generic errors.
 */
export function messageFromApiFailure(response, payload) {
  const status = response?.status ?? 0

  if (status === 429) {
    const retry = response.headers?.get?.('Retry-After')
    const seconds = retry != null ? parseInt(String(retry).trim(), 10) : NaN
    if (Number.isFinite(seconds) && seconds > 0) {
      if (seconds >= 60) {
        const mins = Math.ceil(seconds / 60)
        return `Too many submissions for now. For security, please wait about ${mins} minute${
          mins === 1 ? '' : 's'
        } before trying again.`
      }
      return `Too many submissions for now. For security, please wait about ${seconds} second${
        seconds === 1 ? '' : 's'
      } before trying again.`
    }
    return 'Too many submissions from this browser or for this address. Please wait a few minutes before trying again. This limit protects the service from abuse.'
  }

  if (status === 401 || status === 403) {
    return 'You are not allowed to do that. If you think this is a mistake, try again later or contact the team.'
  }

  if (status === 502 || status === 503 || status === 504) {
    return 'The service is temporarily busy or unavailable. Please try again in a few minutes.'
  }

  if (status === 400 || status === 422) {
    return formatDetail(payload?.detail) || 'The information could not be accepted. Check your input and try again.'
  }

  if (status >= 500) {
    return 'The server had a problem processing your request. Please try again later.'
  }

  if (status > 0) {
    const fromDetail = formatDetail(payload?.detail)
    if (fromDetail) {
      return fromDetail
    }
    return `Something went wrong (HTTP ${status}). Please try again.`
  }

  return 'Network or connection error. Check your connection and try again.'
}

function formatDetail(detail) {
  if (detail == null) {
    return ''
  }
  if (typeof detail === 'string') {
    return detail.trim() || ''
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (item == null) {
          return ''
        }
        if (typeof item === 'string') {
          return item
        }
        if (typeof item === 'object' && item.msg) {
          return String(item.msg)
        }
        return ''
      })
      .filter(Boolean)
    return parts.join(' ').trim()
  }
  if (typeof detail === 'object' && detail.msg) {
    return String(detail.msg)
  }
  return ''
}
