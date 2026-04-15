import { GOOD_MATCH_THRESHOLD, REVIEW_MATCH_THRESHOLD, normalizeText } from './shared.js'
import { buildPlan as buildPlanFromFields } from './matching.js'

const EventCtor = globalThis.Event || class Event {
  constructor(type, init = {}) {
    this.type = type
    this.bubbles = Boolean(init.bubbles)
  }
}

export function isFieldRequired({ required = false, ariaRequired = false, label = '' } = {}) {
  if (required) return true
  if (ariaRequired) return true
  return String(label || '').includes('*')
}

export function getLabelFor(element, root = document) {
  if (!element) return ''

  if (element.id) {
    const escapedId = globalThis.CSS?.escape ? globalThis.CSS.escape(element.id) : element.id.replace(/"/g, '\\"')
    const label = root.querySelector(`label[for="${escapedId}"]`)
    if (label?.textContent) return label.textContent.trim()
  }

  const wrappingLabel = element.closest?.('label')
  if (wrappingLabel) {
    const clone = wrappingLabel.cloneNode(true)
    clone.querySelectorAll?.('input, textarea, select')?.forEach((child) => child.remove())
    const text = clone.textContent?.trim()
    if (text) return text
  }

  // Real application forms are inconsistent, so the fallback chain broadens
  // from explicit labels to nearby text only after stronger signals fail.
  const ariaLabel = element.getAttribute?.('aria-label')
  if (ariaLabel) return ariaLabel

  const placeholder = element.getAttribute?.('placeholder')
  if (placeholder) return placeholder

  const dataLabel = element.getAttribute?.('data-label')
  if (dataLabel) return dataLabel

  const parent = element.parentElement
  if (parent) {
    const nearbyLabel = parent.querySelector?.('span:not(.error), .label, .field-label')
    if (nearbyLabel?.textContent?.trim()?.length < 60) return nearbyLabel.textContent.trim()
    const text = parent.innerText?.trim()
    if (text && text.length < 80) return text
  }

  return ''
}

function isVisibleField(element) {
  if (!element) return false
  const rect = typeof element.getBoundingClientRect === 'function'
    ? element.getBoundingClientRect()
    : { width: 0, height: 0 }
  return rect.width > 0 || rect.height > 0 || element.offsetParent !== null
}

export function discoverFields(root = document) {
  return Array.from(root.querySelectorAll('input, textarea, select'))
    .filter((element) => !element.disabled)
    .filter((element) => element.type !== 'hidden')
    .filter((element) => !['submit', 'button', 'reset'].includes(element.type))
    .filter((element) => {
      const labelNorm = normalizeText(getLabelFor(element, root))
      return !(labelNorm.includes('search') && !labelNorm.includes('job'))
    })
    .filter(isVisibleField)
    .map((element) => {
      const label = getLabelFor(element, root)
      return {
        el: element,
        label,
        labelNorm: normalizeText(label),
        name: element.getAttribute?.('name') || '',
        id: element.id || '',
        required: isFieldRequired({
          required: Boolean(element.required),
          ariaRequired: element.getAttribute?.('aria-required') === 'true',
          label,
        }),
        tagName: element.tagName?.toLowerCase?.() || '',
        inputType: element.type || '',
      }
    })
}

export function buildDomPlan(tokenMap, root = document) {
  return buildPlanFromFields(discoverFields(root), tokenMap || {})
}

export function fillField(element, value) {
  try {
    if (!element) return false

    if (element.tagName?.toLowerCase?.() === 'select') {
      const options = Array.from(element.options || [])
      const normalizedValue = normalizeText(String(value))
      let match = options.find((option) => normalizeText(option.textContent) === normalizedValue)
      if (!match) match = options.find((option) => normalizeText(option.value) === normalizedValue)
      if (!match) match = options.find((option) => normalizeText(option.textContent).includes(normalizedValue))
      if (!match) {
        match = options.find((option) => {
          const optionText = normalizeText(option.textContent)
          return optionText.length > 1 && normalizedValue.includes(optionText)
        })
      }
      if (!match) return false
      element.value = match.value
    } else if (element.type === 'checkbox') {
      const shouldCheck = value === true || value === 'true' || value === '1'
      if (element.checked !== shouldCheck) element.click?.()
      return true
    } else if (element.type === 'radio') {
      const normalizedValue = normalizeText(String(value))
      if (normalizeText(element.value) !== normalizedValue) return false
      element.click?.()
      return true
    } else {
      element.focus?.()
      element.value = String(value)
    }

    element.dispatchEvent?.(new EventCtor('input', { bubbles: true }))
    element.dispatchEvent?.(new EventCtor('change', { bubbles: true }))
    element.dispatchEvent?.(new EventCtor('blur', { bubbles: true }))
    return true
  } catch {
    return false
  }
}

export function fillPlan(plan, tokenMap) {
  let filled = 0
  const sortedPlan = [...(Array.isArray(plan) ? plan : [])].sort((left, right) => {
    const leftPriority = left.matchPath?.endsWith('.is_current') ? 0 : 1
    const rightPriority = right.matchPath?.endsWith('.is_current') ? 0 : 1
    return leftPriority - rightPriority
  })

  for (const item of sortedPlan) {
    if (!item.matchPath || item.matchScore < REVIEW_MATCH_THRESHOLD) continue

    const value = tokenMap?.[item.matchPath]
    if (value === null || value === undefined || value === '') continue

    // Avoid filling stale end dates into entries that are explicitly marked as
    // current in the source token map.
    if (item.matchPath.match(/\.(end_month|end_year|end_date)$/)) {
      const prefix = item.matchPath.replace(/\.(end_month|end_year|end_date)$/, '')
      if (tokenMap?.[`${prefix}.is_current`] === true) continue
    }

    if (fillField(item.el, value)) filled += 1
  }

  return filled
}

export function computePlanStats(plan) {
  const normalizedPlan = Array.isArray(plan) ? plan : []
  const good = normalizedPlan.filter((item) => item.matchPath && item.matchScore >= GOOD_MATCH_THRESHOLD).length
  const review = normalizedPlan.filter(
    (item) => item.matchPath && item.matchScore >= REVIEW_MATCH_THRESHOLD && item.matchScore < GOOD_MATCH_THRESHOLD
  ).length
  const missing = normalizedPlan.filter((item) => item.required && !item.matchPath).length

  return {
    total: normalizedPlan.length,
    matched: good + review,
    good,
    review,
    missing,
  }
}

export function clearHighlights(root = document) {
  root.querySelectorAll('.uah-fill-good, .uah-fill-review, .uah-fill-missing')
    .forEach((element) => element.classList.remove('uah-fill-good', 'uah-fill-review', 'uah-fill-missing'))
}

export function applyHighlights(plan) {
  ;(Array.isArray(plan) ? plan : []).forEach((item) => {
    if (!item.el) return
    if (item.matchPath && item.matchScore >= GOOD_MATCH_THRESHOLD) {
      item.el.classList.add('uah-fill-good')
    } else if (item.matchPath && item.matchScore >= REVIEW_MATCH_THRESHOLD) {
      item.el.classList.add('uah-fill-review')
    } else if (item.required) {
      item.el.classList.add('uah-fill-missing')
    }
  })
}
