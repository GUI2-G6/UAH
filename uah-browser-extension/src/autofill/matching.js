import { normalizeText } from './shared.js'
import { resolveFieldPolicy } from './resolver.js'

const DIRECT_NAME_MAP = {
  first_name: 'personal_info.first_name',
  middle_name: 'personal_info.middle_name',
  middle_initial: 'personal_info.middle_initial',
  last_name: 'personal_info.last_name',
  legal_name: 'personal_info.full_legal_name',
  full_legal_name: 'personal_info.full_legal_name',
  preferred_name: 'personal_info.preferred_name',
  suffix: 'personal_info.suffix',
  email: 'personal_info.email',
  phone: 'personal_info.phone',
  address: 'personal_info.address',
  street_address: 'personal_info.address',
  city: 'personal_info.city',
  state: 'personal_info.state',
  zip: 'personal_info.zip',
  zipcode: 'personal_info.zip',
  postal_code: 'personal_info.zip',
  linkedin: 'personal_info.linkedin',
  website: 'personal_info.website',
  portfolio: 'personal_info.website',
  summary: 'summary',
  work_auth: 'work_auth',
  work_authorization: 'work_auth',
  authorized_to_work: 'work_auth',
  requires_sponsorship: 'requires_sponsorship',
  sponsorship_required: 'requires_sponsorship',
  years_experience: 'years_experience',
  experience_years: 'years_experience',
  professional_links: 'professional_links_text',
  professional_links_text: 'professional_links_text',
  additional_links: 'professional_links_text',
}

const INDEXED_FIELD_MAP = {
  education: {
    school: 'institution',
    institution: 'institution',
    university: 'institution',
    college: 'institution',
    degree: 'degree',
    degree_type: 'degree',
    field_of_study: 'field_of_study',
    field: 'field_of_study',
    major: 'field_of_study',
    concentration: 'field_of_study',
    gpa: 'gpa',
    start_date: 'start_date',
    start_month: 'start_month',
    start_year: 'start_year',
    end_date: 'end_date',
    end_month: 'end_month',
    end_year: 'end_year',
    currently_enrolled: 'is_current',
    currently_attend_here: 'is_current',
    is_current: 'is_current',
    graduation: 'end_date',
    honors: 'honors',
    coursework: 'relevant_coursework',
  },
  work_experience: {
    title: 'title',
    job_title: 'title',
    position: 'title',
    role: 'title',
    company: 'company',
    employer: 'company',
    organization: 'company',
    location: 'location',
    start_date: 'start_date',
    start_month: 'start_month',
    start_year: 'start_year',
    end_date: 'end_date',
    end_month: 'end_month',
    end_year: 'end_year',
    currently_work_here: 'is_current',
    is_current: 'is_current',
    description: 'bullets',
    duties: 'bullets',
    responsibilities: 'bullets',
  },
  projects: {
    name: 'name',
    project_name: 'name',
    description: 'description',
    technologies: 'technologies',
    url: 'url',
    date: 'date',
  },
}

const INDEXED_RE = /^(\w+)\[(\d+)\]\.(\w+)$/

const SYNONYMS = [
  { path: 'personal_info.first_name', terms: ['first name', 'given name', 'fname', 'legal first name', 'legal name first'] },
  { path: 'personal_info.middle_name', terms: ['middle name', 'm name', 'middle'] },
  { path: 'personal_info.middle_initial', terms: ['middle initial', 'mi', 'm i', 'middle initial optional'] },
  { path: 'personal_info.last_name', terms: ['last name', 'surname', 'family name', 'lname', 'legal last name', 'legal name last'] },
  { path: 'personal_info.full_legal_name', terms: ['full legal name', 'legal name', 'name as shown on id', 'full name legal'] },
  { path: 'personal_info.preferred_name', terms: ['preferred name', 'nickname', 'chosen name'] },
  { path: 'personal_info.suffix', terms: ['suffix', 'name suffix', 'jr', 'sr', 'ii', 'iii', 'iv'] },
  { path: 'personal_info.email', terms: ['email', 'email address', 'e mail', 'e mail address'] },
  { path: 'personal_info.phone', terms: ['phone', 'phone number', 'mobile', 'cell', 'telephone', 'contact number'] },
  { path: 'personal_info.address', terms: ['address', 'street address', 'address line 1', 'address line', 'mailing address'] },
  { path: 'personal_info.city', terms: ['city', 'city town'] },
  { path: 'personal_info.state', terms: ['state', 'state province', 'region', 'province'] },
  { path: 'personal_info.zip', terms: ['zip', 'zip code', 'postal code', 'zipcode'] },
  { path: 'personal_info.linkedin', terms: ['linkedin', 'linkedin url', 'linkedin profile'] },
  { path: 'personal_info.website', terms: ['website', 'portfolio', 'personal website', 'homepage', 'web page'] },
  { path: 'education[0].institution', terms: ['school', 'university', 'institution', 'college', 'school name', 'university name'] },
  { path: 'education[0].degree', terms: ['degree', 'degree type', 'level of education'] },
  { path: 'education[0].field_of_study', terms: ['field of study', 'major', 'concentration', 'area of study', 'program'] },
  { path: 'education[0].gpa', terms: ['gpa', 'grade point average', 'grade point', 'cumulative gpa'] },
  { path: 'education[0].start_date', terms: ['education start', 'edu start date', 'from date education'] },
  { path: 'education[0].end_date', terms: ['education end', 'edu end date', 'graduation date', 'expected graduation', 'completion date'] },
  { path: 'education[0].is_current', terms: ['i currently attend here', 'currently enrolled', 'currently attending', 'still enrolled', 'current student'] },
  { path: 'work_experience[0].company', terms: ['company', 'employer', 'organization', 'company name', 'employer name'] },
  { path: 'work_experience[0].title', terms: ['job title', 'position', 'title', 'role', 'position title'] },
  { path: 'work_experience[0].location', terms: ['work location', 'job location', 'location'] },
  { path: 'work_experience[0].start_date', terms: ['work start', 'employment start', 'start date', 'from'] },
  { path: 'work_experience[0].end_date', terms: ['work end', 'employment end', 'end date', 'to'] },
  { path: 'work_experience[0].is_current', terms: ['i currently work here', 'currently employed', 'current position', 'currently working', 'present position'] },
  { path: 'work_experience[0].bullets', terms: ['description', 'duties', 'responsibilities', 'job description'] },
  { path: 'work_experience[0].bullets', terms: ['role description', 'describe your role', 'role summary'] },
  { path: 'summary', terms: ['summary', 'objective', 'professional summary', 'cover letter', 'about'] },
  { path: 'work_auth', terms: ['work auth', 'work authorization', 'authorized to work', 'legally authorized to work', 'authorization to work', 'eligible to work'] },
  { path: 'requires_sponsorship', terms: ['requires sponsorship', 'sponsorship required', 'need sponsorship', 'visa sponsorship', 'require sponsorship'] },
  { path: 'years_experience', terms: ['years of experience', 'total years of experience', 'experience in years', 'relevant experience years'] },
  { path: 'professional_links_text', terms: ['professional links', 'additional links', 'github', 'github profile', 'additional websites'] },
]

function pickFirstTokenPath(tokenMap, pattern) {
  return Object.keys(tokenMap || {}).find((key) => pattern.test(String(key)))
}

function matchWorkdaySpecialLabels(labelNorm, tokenMap) {
  const normalizedLabel = String(labelNorm || '')
  if (!normalizedLabel) return { path: null, score: 0 }

  if (normalizedLabel.includes('skills') || normalizedLabel.includes('type to add skills')) {
    const skillsPath = pickFirstTokenPath(tokenMap, /^skills\./)
    if (skillsPath) return { path: skillsPath, score: 0.92 }
  }

  if (normalizedLabel === 'from') {
    const startDatePath = pickFirstTokenPath(tokenMap, /^work_experience\[\d+\]\.start_date$/)
    if (startDatePath) return { path: startDatePath, score: 0.9 }
    const fallbackPath = pickFirstTokenPath(tokenMap, /^work_experience\[\d+\]\.(start_month|start_year)$/)
    if (fallbackPath) return { path: fallbackPath, score: 0.75 }
  }

  if (normalizedLabel === 'to') {
    const endDatePath = pickFirstTokenPath(tokenMap, /^work_experience\[\d+\]\.end_date$/)
    if (endDatePath) return { path: endDatePath, score: 0.9 }
    const fallbackPath = pickFirstTokenPath(tokenMap, /^work_experience\[\d+\]\.(end_month|end_year)$/)
    if (fallbackPath) return { path: fallbackPath, score: 0.75 }
  }

  return { path: null, score: 0 }
}

function sanitizeFieldName(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

export function resolveNameToPath(fieldName) {
  const normalizedFieldName = sanitizeFieldName(fieldName)
  if (!normalizedFieldName) return null

  if (DIRECT_NAME_MAP[normalizedFieldName]) return DIRECT_NAME_MAP[normalizedFieldName]

  const indexedMatch = normalizedFieldName.match(INDEXED_RE)
  if (indexedMatch) {
    const [, section, index, field] = indexedMatch
    const sectionMap = INDEXED_FIELD_MAP[section]
    const resumeField = sectionMap?.[field] || field
    return `${section}[${index}].${resumeField}`
  }

  const currentWorkMatch = normalizedFieldName.match(/^currently_work_here_(\d+)$/)
  if (currentWorkMatch) return `work_experience[${currentWorkMatch[1]}].is_current`

  return null
}

export function scoreMatch(labelNorm, terms) {
  let best = 0
  for (const term of terms) {
    const normalizedTerm = normalizeText(term)
    if (!normalizedTerm) continue
    if (labelNorm === normalizedTerm) {
      best = Math.max(best, 1)
    } else if (labelNorm.includes(normalizedTerm)) {
      best = Math.max(best, 0.85)
    } else if (normalizedTerm.includes(labelNorm) && labelNorm.length > 3) {
      best = Math.max(best, 0.75)
    } else {
      const labelWords = new Set(labelNorm.split(' '))
      const termWords = normalizedTerm.split(' ')
      const overlap = termWords.filter((word) => labelWords.has(word)).length
      if (overlap > 0) {
        best = Math.max(best, Math.min(0.7, overlap / Math.max(1, termWords.length)))
      }
    }
  }
  return best
}

export function matchLabelToPath(labelNorm, tokenMap) {
  let best = { path: null, score: 0 }

  const workdaySpecial = matchWorkdaySpecialLabels(labelNorm, tokenMap)
  if (workdaySpecial.score > best.score) {
    best = workdaySpecial
  }

  for (const synonym of SYNONYMS) {
    if (tokenMap[synonym.path] === undefined) continue
    const score = scoreMatch(labelNorm, synonym.terms)
    if (score > best.score) {
      best = { path: synonym.path, score }
    }
  }

  if (best.score < 0.5) {
    for (const key of Object.keys(tokenMap || {})) {
      const lastPart = key.split('.').pop()?.replace(/\[\d+\]/g, '') || ''
      const normalizedKey = normalizeText(lastPart.replace(/_/g, ' '))
      if (normalizedKey && labelNorm.includes(normalizedKey) && normalizedKey.length > 2) {
        best = { path: key, score: 0.55 }
        break
      }
    }
  }

  return best
}

export function buildPlan(fields, tokenMap) {
  return (Array.isArray(fields) ? fields : []).map((field) => {
    let matchPath = null
    let matchScore = 0
    let matchReason = 'no_match'

    const namePath = resolveNameToPath(field.name)
    if (namePath && tokenMap[namePath] !== undefined) {
      matchPath = namePath
      matchScore = 1
      matchReason = 'name'
    }

    if (!matchPath) {
      const idPath = resolveNameToPath(field.id)
      if (idPath && tokenMap[idPath] !== undefined) {
        matchPath = idPath
        matchScore = 0.95
        matchReason = 'id'
      }
    }

    if (!matchPath || matchScore < 0.8) {
      const synonymResult = matchLabelToPath(field.labelNorm || '', tokenMap)
      if (synonymResult.score > matchScore) {
        matchPath = synonymResult.path
        matchScore = synonymResult.score
        matchReason = 'label'
      }
    }

    const policy = resolveFieldPolicy(field, {
      matchPath,
      matchScore,
      reason: matchReason,
    })

    return {
      ...field,
      matchPath,
      matchScore,
      matchReason,
      confidenceClass: policy.confidenceClass,
      sensitive: policy.sensitive,
      requiresApproval: policy.requiresApproval,
      resolverReason: policy.reason,
    }
  })
}
