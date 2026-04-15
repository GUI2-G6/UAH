export const GOOD_MATCH_THRESHOLD = 0.75
export const REVIEW_MATCH_THRESHOLD = 0.5

const PRESENT_TOKENS_RE = /^(?:present|current|ongoing|now|in[- ]?progress)$/i

function stringifyValue(value) {
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return ''
}

export function normalizeText(value) {
  return stringifyValue(value)
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[^a-z0-9 ]/g, '')
    .trim()
}

export function splitDate(value) {
  const raw = stringifyValue(value).trim()
  if (!raw) return { month: null, year: null, isPresent: false }
  if (PRESENT_TOKENS_RE.test(raw)) return { month: null, year: null, isPresent: true }

  const expectedMatch = raw.match(/^(?:Expected|Anticipated)\s+([A-Za-z]+)\s+(\d{4})$/i)
  if (expectedMatch) {
    return { month: expectedMatch[1], year: expectedMatch[2], isPresent: false }
  }

  const monthYearMatch = raw.match(/^([A-Za-z]+)\s+(\d{4})$/i)
  if (monthYearMatch) {
    return { month: monthYearMatch[1], year: monthYearMatch[2], isPresent: false }
  }

  const yearOnlyMatch = raw.match(/^(\d{4})$/)
  if (yearOnlyMatch) {
    return { month: null, year: yearOnlyMatch[1], isPresent: false }
  }

  return { month: null, year: null, isPresent: false }
}

function setJoinedToken(target, path, value, separator = ', ') {
  if (!Array.isArray(value) || !value.length) return
  target[path] = value.map((item) => stringifyValue(item)).filter(Boolean).join(separator)
}

export function flattenResume(structured = {}) {
  const tokens = {}

  const personalInfo = structured.personal_info && typeof structured.personal_info === 'object'
    ? structured.personal_info
    : {}
  Object.entries(personalInfo).forEach(([key, value]) => {
    const normalized = stringifyValue(value).trim()
    if (normalized) tokens[`personal_info.${key}`] = normalized
  })

  const summary = stringifyValue(structured.summary).trim()
  if (summary) tokens.summary = summary

  ;(Array.isArray(structured.education) ? structured.education : []).forEach((entry, index) => {
    if (!entry || typeof entry !== 'object') return
    Object.entries(entry).forEach(([key, value]) => {
      if (value == null) return
      if (Array.isArray(value)) {
        setJoinedToken(tokens, `education[${index}].${key}`, value)
        return
      }
      if (typeof value === 'boolean') {
        tokens[`education[${index}].${key}`] = value
        return
      }
      const normalized = stringifyValue(value).trim()
      if (normalized) tokens[`education[${index}].${key}`] = normalized
    })

    if (entry.start_date) {
      const startDate = splitDate(entry.start_date)
      if (startDate.month) tokens[`education[${index}].start_month`] = startDate.month
      if (startDate.year) tokens[`education[${index}].start_year`] = startDate.year
    }

    if (entry.is_current === true) {
      tokens[`education[${index}].is_current`] = true
    }

    if (entry.end_date) {
      const endDate = splitDate(entry.end_date)
      if (endDate.isPresent) {
        tokens[`education[${index}].is_current`] = true
      } else {
        if (endDate.month) tokens[`education[${index}].end_month`] = endDate.month
        if (endDate.year) tokens[`education[${index}].end_year`] = endDate.year
      }
    }
  })

  ;(Array.isArray(structured.work_experience) ? structured.work_experience : []).forEach((entry, index) => {
    if (!entry || typeof entry !== 'object') return
    Object.entries(entry).forEach(([key, value]) => {
      if (value == null) return
      if (Array.isArray(value)) {
        setJoinedToken(tokens, `work_experience[${index}].${key}`, value, key === 'bullets' ? '\n' : ', ')
        return
      }
      if (typeof value === 'boolean') {
        tokens[`work_experience[${index}].${key}`] = value
        return
      }
      const normalized = stringifyValue(value).trim()
      if (normalized) tokens[`work_experience[${index}].${key}`] = normalized
    })

    if (entry.start_date) {
      const startDate = splitDate(entry.start_date)
      if (startDate.month) tokens[`work_experience[${index}].start_month`] = startDate.month
      if (startDate.year) tokens[`work_experience[${index}].start_year`] = startDate.year
    }

    if (entry.is_current === true) {
      tokens[`work_experience[${index}].is_current`] = true
    }

    if (entry.end_date) {
      const endDate = splitDate(entry.end_date)
      if (endDate.isPresent) {
        tokens[`work_experience[${index}].is_current`] = true
      } else if (!entry.is_current) {
        if (endDate.month) tokens[`work_experience[${index}].end_month`] = endDate.month
        if (endDate.year) tokens[`work_experience[${index}].end_year`] = endDate.year
      }
    }
  })

  const skills = structured.skills && typeof structured.skills === 'object' ? structured.skills : {}
  Object.entries(skills).forEach(([key, value]) => {
    setJoinedToken(tokens, `skills.${key}`, value)
  })

  ;(Array.isArray(structured.projects) ? structured.projects : []).forEach((entry, index) => {
    if (!entry || typeof entry !== 'object') return
    Object.entries(entry).forEach(([key, value]) => {
      if (value == null) return
      if (Array.isArray(value)) {
        setJoinedToken(tokens, `projects[${index}].${key}`, value)
        return
      }
      const normalized = stringifyValue(value).trim()
      if (normalized) tokens[`projects[${index}].${key}`] = normalized
    })
  })

  ;(Array.isArray(structured.certifications) ? structured.certifications : []).forEach((entry, index) => {
    if (!entry || typeof entry !== 'object') return
    Object.entries(entry).forEach(([key, value]) => {
      const normalized = stringifyValue(value).trim()
      if (normalized) tokens[`certifications[${index}].${key}`] = normalized
    })
  })

  ;['awards', 'activities', 'volunteer'].forEach((key) => {
    const value = structured[key]
    if (Array.isArray(value) && value.length) {
      tokens[key] = value.map((item) => stringifyValue(item)).filter(Boolean).join('\n')
    }
  })

  return tokens
}
