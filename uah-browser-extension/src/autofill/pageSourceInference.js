import { normalizeText } from './shared.js'

function tryParseJson(value) {
  const text = String(value || '').trim()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function getFieldLabel(element) {
  const candidates = [
    element?.getAttribute?.('aria-label'),
    element?.getAttribute?.('data-label'),
    element?.getAttribute?.('placeholder'),
    element?.name,
    element?.id,
  ]
  return candidates.find((value) => String(value || '').trim()) || ''
}

function collectInlineJson(doc) {
  if (!doc || typeof doc.querySelectorAll !== 'function') return []
  const scripts = doc.querySelectorAll('script[type="application/json"], script[type="application/ld+json"], script:not([src])')
  return Array.from(scripts || [])
    .map((node) => tryParseJson(node?.textContent))
    .filter(Boolean)
}

function walkForFieldOptions(node, normalizedLabel, results = []) {
  if (!node || typeof node !== 'object') return results

  if (Array.isArray(node)) {
    node.forEach((item) => walkForFieldOptions(item, normalizedLabel, results))
    return results
  }

  const label = normalizeText(node.label || node.name || node.fieldLabel || node.question || '')
  const options = Array.isArray(node.options)
    ? node.options
    : Array.isArray(node.choices)
      ? node.choices
      : null

  if (label && label === normalizedLabel && options?.length) {
    results.push(
      ...options
        .map((option) => {
          if (typeof option === 'string') return option
          if (typeof option === 'number' || typeof option === 'boolean') return String(option)
          if (option && typeof option === 'object') {
            return option.label || option.text || option.value || null
          }
          return null
        })
        .filter(Boolean),
    )
  }

  Object.values(node).forEach((value) => walkForFieldOptions(value, normalizedLabel, results))
  return results
}

export function inferDropdownCandidates({ element, desiredValue, doc = globalThis.document } = {}) {
  const normalizedLabel = normalizeText(getFieldLabel(element))
  const normalizedValue = normalizeText(desiredValue)
  if (!normalizedLabel || !normalizedValue) {
    return { candidates: [], confidence: 'none', source: null }
  }

  const jsonBlobs = collectInlineJson(doc)
  const candidates = []
  jsonBlobs.forEach((blob) => {
    candidates.push(...walkForFieldOptions(blob, normalizedLabel))
  })

  const deduped = [...new Set(candidates.map((item) => String(item).trim()).filter(Boolean))]
  const exact = deduped.filter((candidate) => normalizeText(candidate) === normalizedValue)

  if (exact.length) {
    return {
      candidates: exact,
      confidence: 'high',
      source: 'inline-json',
    }
  }

  const partial = deduped.filter((candidate) => normalizeText(candidate).includes(normalizedValue))
  return {
    candidates: partial,
    confidence: partial.length ? 'low' : 'none',
    source: partial.length ? 'inline-json' : null,
  }
}

export function resolveDropdownInference({ desiredValue, inferred } = {}) {
  const confidence = String(inferred?.confidence || 'none')
  const candidates = Array.isArray(inferred?.candidates) ? inferred.candidates.filter(Boolean) : []
  if (confidence !== 'high' || !candidates.length) {
    return {
      accepted: false,
      value: null,
      candidates,
      source: inferred?.source || null,
    }
  }

  return {
    accepted: true,
    value: candidates[0] || String(desiredValue || ''),
    candidates,
    source: inferred?.source || null,
  }
}
