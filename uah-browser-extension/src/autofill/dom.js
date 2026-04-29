import { GOOD_MATCH_THRESHOLD, REVIEW_MATCH_THRESHOLD, normalizeText } from './shared.js'
import { buildPlan as buildPlanFromFields } from './matching.js'
import { fillComboboxField, fillComboboxMultiValueField } from './dropdown.js'
import { inferDropdownCandidates, resolveDropdownInference } from './pageSourceInference.js'

const EventCtor = globalThis.Event || class Event {
  constructor(type, init = {}) {
    this.type = type
    this.bubbles = Boolean(init.bubbles)
  }
}

const WORKDAY_HOST_RE = /(?:^|\.)(?:[a-z0-9-]+(?:\.wd\d+)?)\.myworkdayjobs\.com$/i

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

function normalizeLabel(value) {
  return normalizeText(String(value || ''))
}

function textOf(element) {
  return String(element?.innerText || element?.textContent || '').trim()
}

function indexedCount(tokenMap, prefix) {
  let max = -1
  for (const key of Object.keys(tokenMap || {})) {
    const match = String(key).match(new RegExp(`^${prefix}\\[(\\d+)\\]\\.`))
    if (!match) continue
    max = Math.max(max, Number(match[1]))
  }
  return max + 1
}

function findVisibleButtons(root = document) {
  if (!root || typeof root.querySelectorAll !== 'function') return []
  return Array.from(root.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"], a'))
    .filter(isVisibleField)
}

function findHeading(root, labelNorm) {
  if (!root || typeof root.querySelectorAll !== 'function') return null
  const headings = Array.from(root.querySelectorAll('h1, h2, h3, h4, h5, h6, legend, [role="heading"], strong'))
  return headings.find((node) => normalizeLabel(textOf(node)) === labelNorm) || null
}

function findSectionButton(root, sectionLabel, buttonLabel) {
  const sectionNorm = normalizeLabel(sectionLabel)
  const buttonNorm = normalizeLabel(buttonLabel)
  const heading = findHeading(root, sectionNorm)
  const buttons = findVisibleButtons(root)
  if (!buttons.length) return null
  if (!heading) {
    return buttons.find((button) => normalizeLabel(textOf(button)) === buttonNorm) || null
  }

  const headingRect = heading.getBoundingClientRect?.() || { top: 0, left: 0 }
  return buttons
    .filter((button) => normalizeLabel(textOf(button)) === buttonNorm)
    .map((button) => ({
      button,
      distance: Math.abs((button.getBoundingClientRect?.().top ?? headingRect.top) - headingRect.top)
        + Math.abs((button.getBoundingClientRect?.().left ?? headingRect.left) - headingRect.left),
    }))
    .sort((a, b) => a.distance - b.distance)[0]?.button || null
}

export function isWorkdayUrl(url = globalThis.location?.href || '') {
  try {
    const parsed = new URL(String(url || ''))
    return WORKDAY_HOST_RE.test(parsed.hostname)
  } catch {
    return false
  }
}

export function expandWorkdaySections(tokenMap = {}, root = document) {
  const workExperienceCount = indexedCount(tokenMap, 'work_experience')
  const educationCount = indexedCount(tokenMap, 'education')
  const languageCount = indexedCount(tokenMap, 'languages')

  let clicks = 0

  const workExperienceExtra = Math.max(0, workExperienceCount - 1)
  for (let index = 0; index < workExperienceExtra; index += 1) {
    const button = findSectionButton(root, 'Work Experience', 'Add Another')
    if (!button) break
    button.click?.()
    clicks += 1
  }

  const educationExtra = Math.max(0, educationCount - 1)
  for (let index = 0; index < educationExtra; index += 1) {
    const button = findSectionButton(root, 'Education', 'Add')
    if (!button) break
    button.click?.()
    clicks += 1
  }

  const languagesExtra = Math.max(0, languageCount - 1)
  for (let index = 0; index < languagesExtra; index += 1) {
    const button = findSectionButton(root, 'Languages', 'Add')
    if (!button) break
    button.click?.()
    clicks += 1
  }

  return { clicks }
}

function formatMonthYear(month, year) {
  const monthMap = {
    january: '01', february: '02', march: '03', april: '04', may: '05', june: '06',
    july: '07', august: '08', september: '09', october: '10', november: '11', december: '12',
  }
  const normalizedMonth = normalizeText(month)
  const monthPart = /^\d{1,2}$/.test(String(month || '').trim())
    ? String(month).trim().padStart(2, '0')
    : monthMap[normalizedMonth] || ''
  const yearPart = String(year || '').trim()
  if (!monthPart || !/^\d{4}$/.test(yearPart)) return null
  return `${monthPart}/${yearPart}`
}

function resolveTokenValue(item, tokenMap) {
  const labelNorm = String(item?.labelNorm || '')
  const directValue = tokenMap?.[item?.matchPath]
  if (labelNorm !== 'from' && labelNorm !== 'to') {
    return directValue
  }

  const path = String(item?.matchPath || '')
  const match = path.match(/^(work_experience\[\d+\])\.(start_month|start_year|end_month|end_year|start_date|end_date)$/)
  if (!match) {
    return directValue
  }

  const prefix = match[1]
  const isStart = labelNorm === 'from'
  const month = tokenMap?.[`${prefix}.${isStart ? 'start_month' : 'end_month'}`]
  const year = tokenMap?.[`${prefix}.${isStart ? 'start_year' : 'end_year'}`]
  const monthYear = formatMonthYear(month, year)
  return monthYear || directValue
}

export function discoverFields(root = document) {
  return Array.from(root.querySelectorAll('input, textarea, select, [role="combobox"]'))
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

export async function fillField(element, value, options = {}) {
  try {
    if (!element) return false

    if (element.tagName?.toLowerCase?.() === 'select') {
      const options = Array.from(element.options || [])
      const normalizedValue = normalizeText(String(value))
      let match = options.find((option) => normalizeText(option.textContent) === normalizedValue)
      if (!match) match = options.find((option) => normalizeText(option.value) === normalizedValue)
      if (!match) match = options.find((option) => normalizeText(option.textContent).includes(normalizedValue))
      if (!match) {
        const compactValue = normalizedValue.replace(/\s+/g, '')
        match = options.find((option) => normalizeText(option.textContent).replace(/\s+/g, '') === compactValue)
      }
      if (!match) {
        match = options.find((option) => {
          const optionText = normalizeText(option.textContent)
          return optionText.length > 1 && normalizedValue.includes(optionText)
        })
      }
      if (!match) return false
      element.value = match.value
    } else if (element.getAttribute?.('role') === 'combobox' || element.getAttribute?.('aria-autocomplete')) {
      const labelNorm = String(options?.planItem?.labelNorm || '')
      const isSkillLike = labelNorm.includes('skills') || labelNorm.includes('type to add skills')
      const inferred = resolveDropdownInference({
        desiredValue: value,
        inferred: inferDropdownCandidates({
          element,
          desiredValue: value,
          doc: options?.doc || element.ownerDocument || document,
        }),
      })
      const candidateValues = inferred.accepted ? [inferred.value, ...inferred.candidates] : []
      const fillCombobox = isSkillLike ? fillComboboxMultiValueField : fillComboboxField
      if (!await fillCombobox(element, value, {
        doc: options?.doc || element.ownerDocument || document,
        candidateValues,
      })) {
        return false
      }
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

export async function fillPlan(plan, tokenMap, options = {}) {
  let filled = 0
  const approvedPaths = new Set(Array.isArray(options?.approvedPaths) ? options.approvedPaths.map((item) => String(item)) : [])
  const sortedPlan = [...(Array.isArray(plan) ? plan : [])].sort((left, right) => {
    const leftPriority = left.matchPath?.endsWith('.is_current') ? 0 : 1
    const rightPriority = right.matchPath?.endsWith('.is_current') ? 0 : 1
    return leftPriority - rightPriority
  })

  for (const item of sortedPlan) {
    if (!item.matchPath || item.matchScore < REVIEW_MATCH_THRESHOLD) continue
    if (item.requiresApproval && !approvedPaths.has(String(item.matchPath))) continue

    const value = resolveTokenValue(item, tokenMap)
    if (value === null || value === undefined || value === '') continue

    // Avoid filling stale end dates into entries that are explicitly marked as
    // current in the source token map.
    if (item.matchPath.match(/\.(end_month|end_year|end_date)$/)) {
      const prefix = item.matchPath.replace(/\.(end_month|end_year|end_date)$/, '')
      if (tokenMap?.[`${prefix}.is_current`] === true) continue
    }

    if (await fillField(item.el, value, { ...options, planItem: item })) filled += 1
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
