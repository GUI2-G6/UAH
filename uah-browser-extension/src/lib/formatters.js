export function displayValue(value, fallback = 'Not set') {
  const normalized = String(value ?? '').trim()
  return normalized || fallback
}

export function displayUserName(user) {
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return fullName || user?.email || 'UAH user'
}

export function formatDateTime(value) {
  if (!value) return 'Unknown'
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

export function buildProfileLocation(profile) {
  return [profile?.city, profile?.state, profile?.zip].filter(Boolean).join(', ')
}

export function buildProfileLinks(profile) {
  return [profile?.linkedin, profile?.portfolio, profile?.professional_links_text].filter(Boolean).join('\n')
}

export function buildResumeName(personalInfo) {
  return [personalInfo?.first_name, personalInfo?.last_name].filter(Boolean).join(' ').trim()
}

export function buildResumeLocation(personalInfo) {
  return [personalInfo?.city, personalInfo?.state, personalInfo?.zip, personalInfo?.country].filter(Boolean).join(', ')
}

export function flattenResumeSkills(skills) {
  const seen = new Set()
  const flattened = []

  for (const value of Object.values(skills || {})) {
    if (!Array.isArray(value)) continue
    for (const skill of value) {
      const normalized = String(skill || '').trim()
      const key = normalized.toLowerCase()
      if (!normalized || seen.has(key)) continue
      seen.add(key)
      flattened.push(normalized)
    }
  }

  return flattened
}

export function summarizeEducation(education = []) {
  return education
    .slice(0, 2)
    .map((entry) => {
      const lineOne = [entry?.degree, entry?.field_of_study].filter(Boolean).join(' in ').trim()
      const lineTwo = [entry?.institution, entry?.end_date || entry?.graduation_date].filter(Boolean).join(' · ').trim()
      return [lineOne, lineTwo].filter(Boolean).join(' — ')
    })
    .filter(Boolean)
}

export function summarizeWork(workExperience = []) {
  return workExperience
    .slice(0, 2)
    .map((entry) => {
      const lineOne = [entry?.title, entry?.company].filter(Boolean).join(' @ ').trim()
      const lineTwo = [entry?.location, entry?.start_date, entry?.end_date || (entry?.is_current ? 'Present' : '')]
        .filter(Boolean)
        .join(' · ')
        .trim()
      return [lineOne, lineTwo].filter(Boolean).join(' — ')
    })
    .filter(Boolean)
}
