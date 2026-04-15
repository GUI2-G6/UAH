import { discoverFields } from '../../autofill/dom.js'
import { normalizeText } from '../../autofill/shared.js'

const COMMON_TITLE_SELECTORS = [
  'h1',
  '[data-automation-id="jobPostingHeader"]',
  '[data-ui="job-title"]',
  '[data-testid="job-name"]',
  '.job-title',
]

const COMMON_COMPANY_SELECTORS = [
  '[data-automation-id="company"]',
  '[data-testid="company-name"]',
  '.company-name',
  '.posting-company',
]

const COMMON_LOCATION_SELECTORS = [
  '[data-automation-id="locations"]',
  '[data-automation-id="locationsList"]',
  '[data-testid="job-location"]',
  '.job-location',
  '.location',
]

const APPLICATION_URL_RE = /\b(apply|application|candidate|job-application|submitapplication)\b/i

function readNodeText(node) {
  if (!node) return ''

  const text = typeof node.textContent === 'string' && node.textContent.trim()
    ? node.textContent
    : node.innerText

  return typeof text === 'string' ? text.trim() : ''
}

function firstText(doc, selectors = []) {
  if (!doc || typeof doc.querySelectorAll !== 'function') return null

  for (const selector of selectors) {
    const nodes = doc.querySelectorAll(selector)
    for (const node of Array.from(nodes || [])) {
      const text = readNodeText(node)
      if (text) return text
    }
  }

  return null
}

function normalizeFieldKey(label) {
  return normalizeText(label).replace(/\s+/g, '-')
}

function createFieldMeta(field = {}) {
  return {
    label: field.label || '',
    type: field.inputType || field.tagName || 'unknown',
    required: Boolean(field.required),
    tagName: field.tagName || '',
    name: field.name || '',
    id: field.id || '',
  }
}

export default class BaseATSAdapter {
  constructor(options = {}) {
    this.document = options.document ?? null
    this.location = options.location ?? null
  }

  getDocument() {
    return this.document ?? globalThis.document ?? null
  }

  getLocationHref() {
    const location = this.location ?? globalThis.location ?? null
    if (typeof location === 'string') return location
    if (location && typeof location.href === 'string') return location.href
    return ''
  }

  toUrl(url = this.getLocationHref()) {
    const rawUrl = String(url || '').trim()
    if (!rawUrl) return null

    try {
      return new URL(rawUrl)
    } catch {
      return null
    }
  }

  queryText(selectors = []) {
    return firstText(this.getDocument(), selectors)
  }

  findFieldByLabel(terms = []) {
    const doc = this.getDocument()
    if (!doc) return null

    const normalizedTerms = (Array.isArray(terms) ? terms : [terms])
      .map((term) => normalizeText(term))
      .filter(Boolean)
    const fields = discoverFields(doc)

    for (const field of fields) {
      const labelNorm = normalizeText(field.label)
      if (!labelNorm) continue
      if (normalizedTerms.some((term) => labelNorm.includes(term))) {
        return createFieldMeta(field)
      }
    }

    return null
  }

  /**
   * Returns true when the adapter supports the provided URL.
   *
   * @param {string} url - Absolute page URL to evaluate.
   * @returns {boolean}
   */
  matches(url) {
    throw new Error(`${this.constructor.name} must implement matches(url).`)
  }

  /**
   * Returns the ATS platform name for this adapter.
   *
   * @returns {string}
   */
  getATSName() {
    throw new Error(`${this.constructor.name} must implement getATSName().`)
  }

  /**
   * Returns the company name for company-specific adapters, or null for base ATS adapters.
   *
   * @returns {string|null}
   */
  getCompanyName() {
    return null
  }

  /**
   * Scrapes visible job details from the current page.
   *
   * @returns {{ title: string|null, company: string|null, location: string|null }}
   */
  detectJobDetails() {
    const title = this.queryText(COMMON_TITLE_SELECTORS)
    const company = this.queryText(COMMON_COMPANY_SELECTORS) || this.getCompanyName()
    const location = this.queryText(COMMON_LOCATION_SELECTORS)

    return {
      title: title || null,
      company: company || null,
      location: location || null,
    }
  }

  /**
   * Returns a map of visible form fields keyed by name, id, normalized label, or index fallback.
   *
   * @returns {Record<string, { label: string, type: string, required: boolean, tagName: string, name: string, id: string }>}
   */
  detectFormFields() {
    const doc = this.getDocument()
    if (!doc) return {}

    const fields = discoverFields(doc)
    const formFields = {}
    const usedKeys = new Set()

    fields.forEach((field, index) => {
      const preferredKeys = [
        String(field.name || '').trim(),
        String(field.id || '').trim(),
        normalizeFieldKey(field.label || ''),
      ].filter(Boolean)

      let key = preferredKeys.find((candidate) => !usedKeys.has(candidate))
      if (!key) {
        key = `field-${index}`
      }

      usedKeys.add(key)
      formFields[key] = createFieldMeta(field)
    })

    return formFields
  }

  /**
   * Returns true when the current page looks like an application form instead of a listing page.
   *
   * @returns {boolean}
   */
  isApplicationPage() {
    if (Object.keys(this.detectFormFields()).length > 0) {
      return true
    }

    return APPLICATION_URL_RE.test(this.getLocationHref())
  }

  /**
   * Describes how complete the adapter's support is for the current ATS instance.
   *
   * @returns {'full'|'partial'|'base'}
   */
  getSupportLevel() {
    return 'base'
  }
}
