import { normalizeText } from './shared.js'

const EventCtor = globalThis.Event || class Event {
  constructor(type, init = {}) {
    this.type = type
    this.bubbles = Boolean(init.bubbles)
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function getDocumentForElement(element, fallback = globalThis.document) {
  return element?.ownerDocument || fallback || globalThis.document || null
}

function getOptionsRoot(element, doc) {
  const listboxId = element?.getAttribute?.('aria-controls')
  if (listboxId && typeof doc?.getElementById === 'function') {
    return doc.getElementById(listboxId) || doc
  }
  return doc
}

function collectOptions(element, doc) {
  const root = getOptionsRoot(element, doc)
  if (!root || typeof root.querySelectorAll !== 'function') return []
  return Array.from(root.querySelectorAll('[role="option"]') || [])
}

function matchOption(options, value) {
  const normalizedValue = normalizeText(String(value))
  const compactValue = normalizedValue.replace(/\s+/g, '')

  let match = options.find((option) => normalizeText(option.textContent || '') === normalizedValue)
  if (!match) match = options.find((option) => normalizeText(option.getAttribute?.('aria-label') || '') === normalizedValue)
  if (!match) match = options.find((option) => normalizeText(option.getAttribute?.('data-value') || '') === normalizedValue)
  if (!match) match = options.find((option) => normalizeText(option.textContent || '').replace(/\s+/g, '') === compactValue)
  if (!match) match = options.find((option) => normalizeText(option.textContent || '').includes(normalizedValue))
  return match || null
}

async function waitForOptions(element, doc, attempts = 3, delayMs = 60) {
  for (let index = 0; index < attempts; index += 1) {
    const options = collectOptions(element, doc)
    if (options.length) return options
    if (index < attempts - 1) {
      await sleep(delayMs)
    }
  }
  return []
}

function dispatchTextEntry(element, value) {
  element.focus?.()
  if ('value' in element) {
    element.value = String(value)
  }
  element.dispatchEvent?.(new EventCtor('input', { bubbles: true }))
  element.dispatchEvent?.(new EventCtor('change', { bubbles: true }))
}

function isExpanded(element) {
  return element?.getAttribute?.('aria-expanded') === 'true'
}

function openCombobox(element) {
  if (isExpanded(element)) return
  element.click?.()
  if (isExpanded(element)) return
  element.dispatchEvent?.(new EventCtor('mousedown', { bubbles: true }))
  element.dispatchEvent?.(new EventCtor('focus', { bubbles: true }))
}

function verifySelection(element, value, option) {
  const expected = normalizeText(String(value))
  const currentValue = normalizeText(element?.value ?? '')
  const currentText = normalizeText(element?.textContent ?? '')
  const optionText = normalizeText(option?.textContent ?? '')

  return currentValue === expected
    || currentText === expected
    || optionText === expected
    || currentValue === optionText
}

function splitMultiValue(value) {
  return String(value || '')
    .split(/\r?\n|,/g)
    .map((item) => item.trim())
    .filter(Boolean)
}

export async function fillComboboxField(element, value, options = {}) {
  if (!element) return false

  const doc = getDocumentForElement(element, options.doc)
  dispatchTextEntry(element, value)
  openCombobox(element)

  let optionList = await waitForOptions(element, doc)
  let match = matchOption(optionList, value)

  if (!match && Array.isArray(options?.candidateValues)) {
    for (const candidate of options.candidateValues) {
      optionList = optionList.length ? optionList : await waitForOptions(element, doc)
      match = matchOption(optionList, candidate)
      if (match) break
    }
  }

  if (!match) return false
  match.click?.()
  if ('value' in element) {
    element.value = String(match.textContent || value)
  }
  element.dispatchEvent?.(new EventCtor('blur', { bubbles: true }))
  return verifySelection(element, value, match)
}

export async function fillComboboxMultiValueField(element, value, options = {}) {
  const tokens = splitMultiValue(value)
  if (!tokens.length) return false

  let filled = 0
  for (const token of tokens) {
    if ('value' in element) {
      element.value = ''
    }
    const ok = await fillComboboxField(element, token, options)
    if (!ok) return false
    filled += 1
  }

  return filled > 0
}
