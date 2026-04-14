import { getAccessToken, getCurrentUser, setAuth } from './auth.js'
import { assertValidEmail, normalizePhone } from './validation.js'

const MOCK_STATE_KEY = 'uah_mock_state_v1'

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '::1', '[::1]'])

const COUNTRY_FIXTURES = [
  { code: 'US', name: 'United States', location_count: 2600 },
  { code: 'CA', name: 'Canada', location_count: 760 },
  { code: 'GB', name: 'United Kingdom', location_count: 540 },
  { code: 'DE', name: 'Germany', location_count: 470 },
]

const CITY_FIXTURES = {
  US: [
    { name: 'Huntsville', admin1: 'AL', country: 'United States', country_code: 'US', latitude: 34.7304, longitude: -86.5861 },
    { name: 'Boston', admin1: 'MA', country: 'United States', country_code: 'US', latitude: 42.3601, longitude: -71.0589 },
    { name: 'Austin', admin1: 'TX', country: 'United States', country_code: 'US', latitude: 30.2672, longitude: -97.7431 },
    { name: 'Seattle', admin1: 'WA', country: 'United States', country_code: 'US', latitude: 47.6062, longitude: -122.3321 },
    { name: 'Denver', admin1: 'CO', country: 'United States', country_code: 'US', latitude: 39.7392, longitude: -104.9903 },
    { name: 'Chicago', admin1: 'IL', country: 'United States', country_code: 'US', latitude: 41.8781, longitude: -87.6298 },
  ],
  CA: [
    { name: 'Toronto', admin1: 'ON', country: 'Canada', country_code: 'CA', latitude: 43.6532, longitude: -79.3832 },
    { name: 'Vancouver', admin1: 'BC', country: 'Canada', country_code: 'CA', latitude: 49.2827, longitude: -123.1207 },
    { name: 'Montreal', admin1: 'QC', country: 'Canada', country_code: 'CA', latitude: 45.5019, longitude: -73.5674 },
  ],
  GB: [
    { name: 'London', admin1: 'England', country: 'United Kingdom', country_code: 'GB', latitude: 51.5072, longitude: -0.1276 },
    { name: 'Manchester', admin1: 'England', country: 'United Kingdom', country_code: 'GB', latitude: 53.4808, longitude: -2.2426 },
    { name: 'Edinburgh', admin1: 'Scotland', country: 'United Kingdom', country_code: 'GB', latitude: 55.9533, longitude: -3.1883 },
  ],
  DE: [
    { name: 'Berlin', admin1: 'Berlin', country: 'Germany', country_code: 'DE', latitude: 52.52, longitude: 13.405 },
    { name: 'Munich', admin1: 'Bavaria', country: 'Germany', country_code: 'DE', latitude: 48.1351, longitude: 11.582 },
    { name: 'Hamburg', admin1: 'Hamburg', country: 'Germany', country_code: 'DE', latitude: 53.5511, longitude: 9.9937 },
  ],
}

const MOCK_LOCATION_PARAM_CAP = 60
const LEVEL_VALUE_ALIASES = {
  internship: 'internship',
  entry: 'entry',
  'entry level': 'entry',
  mid: 'mid',
  'mid level': 'mid',
  senior: 'senior',
  'senior level': 'senior',
  manager: 'manager',
  management: 'manager',
  director: 'director',
  vp: 'vp',
}
const LEVEL_LABELS = {
  internship: 'Internship',
  entry: 'Entry',
  mid: 'Mid',
  senior: 'Senior',
  manager: 'Manager',
  director: 'Director',
  vp: 'VP',
}
const CATEGORY_GROUPS = [
  {
    key: 'tech',
    name: 'Tech',
    muse_categories: [
      'Software Engineer',
      'Software Engineering',
      'Computer and IT',
      'IT',
      'Data and Analytics',
      'Data Science',
      'Design and UX',
      'UX',
      'Science and Engineering',
    ],
  },
  {
    key: 'finance',
    name: 'Finance',
    muse_categories: ['Accounting', 'Accounting and Finance', 'Finance', 'Real Estate'],
  },
  {
    key: 'product',
    name: 'Product',
    muse_categories: ['Product', 'Product Management', 'Project Management'],
  },
  {
    key: 'people',
    name: 'People',
    muse_categories: ['HR', 'Human Resources and Recruitment', 'Recruiting', 'Social Services'],
  },
  {
    key: 'business and operations',
    name: 'Business and Operations',
    muse_categories: ['Business Operations', 'Corporate', 'Operations', 'Office Administration', 'Administration and Office'],
  },
  {
    key: 'sales and marketing',
    name: 'Sales and Marketing',
    muse_categories: [
      'Sales',
      'Marketing',
      'Advertising and Marketing',
      'Public Relations',
      'Media, PR, and Communications',
      'Account Management',
      'Account Management/Customer Success',
    ],
  },
  {
    key: 'customer and support',
    name: 'Customer and Support',
    muse_categories: ['Customer Service', 'Education', 'Legal Services'],
  },
]
const CATEGORY_ALIAS = {
  technology: 'Tech',
  engineering: 'Tech',
  tech: 'Tech',
  fintech: 'Finance',
  finance: 'Finance',
  product: 'Product',
  people: 'People',
  hr: 'People',
  operations: 'Business and Operations',
  business: 'Business and Operations',
  sales: 'Sales and Marketing',
  marketing: 'Sales and Marketing',
  support: 'Customer and Support',
}
const CATEGORY_GROUP_BY_NAME = CATEGORY_GROUPS.reduce((acc, group) => {
  acc[group.name.toLowerCase()] = group
  return acc
}, {})

const PROVIDER_ATTRIBUTION_FIXTURES = {
  the_muse: {
    provider: 'the_muse',
    default_state: 'active',
    sweep_mode: 'category',
    scheduled_interval_minutes: null,
    ingest_enabled: true,
    display_enabled: true,
    scheduled_enabled: true,
    status: 'active',
    attribution: {
      label: 'The Muse',
      url: 'https://www.themuse.com',
      required: true,
      logo_url: null,
    },
  },
  arbeitnow: {
    provider: 'arbeitnow',
    default_state: 'active',
    sweep_mode: 'global',
    scheduled_interval_minutes: 120,
    ingest_enabled: true,
    display_enabled: true,
    scheduled_enabled: true,
    status: 'active',
    attribution: {
      label: 'Arbeitnow',
      url: 'https://www.arbeitnow.com',
      required: false,
      logo_url: null,
    },
  },
  findwork: {
    provider: 'findwork',
    default_state: 'dormant',
    sweep_mode: 'global',
    scheduled_interval_minutes: 240,
    ingest_enabled: false,
    display_enabled: false,
    scheduled_enabled: false,
    status: 'dormant',
    attribution: {
      label: 'Findwork',
      url: 'https://findwork.dev',
      required: false,
      logo_url: null,
    },
  },
  jooble: {
    provider: 'jooble',
    default_state: 'dormant',
    sweep_mode: 'matrix',
    scheduled_interval_minutes: 360,
    ingest_enabled: false,
    display_enabled: false,
    scheduled_enabled: false,
    status: 'dormant',
    attribution: {
      label: 'Jooble',
      url: 'https://jooble.org',
      required: false,
      logo_url: null,
    },
  },
  adzuna: {
    provider: 'adzuna',
    default_state: 'dormant',
    sweep_mode: 'category',
    scheduled_interval_minutes: 720,
    ingest_enabled: false,
    display_enabled: false,
    scheduled_enabled: false,
    status: 'dormant',
    attribution: {
      label: 'Jobs by Adzuna',
      url: 'https://www.adzuna.co.uk',
      required: true,
      logo_url: 'https://www.adzuna.co.uk/press.html',
      salary_label: 'Adzuna Jobsworth',
      salary_url: 'https://www.adzuna.co.uk/jobs/salary-predictor.html',
    },
  },
  careerjet: {
    provider: 'careerjet',
    default_state: 'dormant',
    sweep_mode: 'disabled',
    scheduled_interval_minutes: null,
    ingest_enabled: false,
    display_enabled: false,
    scheduled_enabled: false,
    status: 'dormant',
    attribution: {
      label: 'Careerjet',
      url: 'https://www.careerjet.com',
      required: false,
      logo_url: null,
    },
  },
}

const JOB_FIXTURES = [
  {
    id: 'mock-job-1001',
    provider: 'the_muse',
    provider_job_id: '7619281',
    name: 'Frontend Engineer (Vue)',
    short_name: 'Frontend Engineer',
    short_description: 'Build polished Vue features, tighten shared UI patterns, and ship product improvements with a hybrid team.',
    company: 'Atlas Systems',
    locations: ['Huntsville, AL'],
    location_country_code: 'US',
    location_country_name: 'United States',
    levels: ['Mid Level'],
    categories: ['Software Engineer'],
    tags: ['Vue', 'TypeScript', 'UI'],
    type: 'Full Time',
    model_type: 'hybrid',
    work_mode_reason: 'Hybrid collaboration required',
    has_remote: true,
    has_hybrid: true,
    is_local_compatible_remote: true,
    local_compatibility_reason: 'Remote-friendly in selected region',
    location_constraints: { countries: ['US'], states: ['AL', 'TX'] },
    quality_score: 0.94,
    publication_date: '2026-04-05T09:00:00Z',
    provider_url: 'https://www.themuse.com/jobs/atlas-systems/frontend-engineer-vue',
    job_url: 'https://www.themuse.com/jobs/atlas-systems/frontend-engineer-vue',
    apply_url: 'https://jobs.ashbyhq.com/atlas-systems/frontend-123',
    apply_portal: 'ashby',
    source_tags: ['provider:the_muse', 'apply_portal:ashby'],
    contents: 'Build and ship frontend features with Vue and modern tooling.',
  },
  {
    id: 'mock-job-1002',
    provider: 'arbeitnow',
    provider_job_id: 'backend-python-engineer',
    name: 'Backend Python Engineer',
    short_name: 'Backend Engineer',
    short_description: 'Own API performance, queue reliability, and backend foundations for a fast-moving data platform.',
    company: 'Data Forge',
    locations: ['Austin, TX'],
    location_country_code: 'US',
    location_country_name: 'United States',
    levels: ['Senior Level'],
    categories: ['Software Engineer'],
    tags: ['Python', 'FastAPI', 'Postgres'],
    type: 'Full Time',
    model_type: 'onsite',
    work_mode_reason: 'Onsite lab access required',
    has_remote: false,
    has_hybrid: false,
    is_local_compatible_remote: false,
    local_compatibility_reason: '',
    location_constraints: { countries: ['US'], states: ['TX'] },
    quality_score: 0.91,
    publication_date: '2026-04-02T11:30:00Z',
    provider_url: 'https://jobs.ashbyhq.com/data-forge/backend-python-1002',
    job_url: 'https://jobs.ashbyhq.com/data-forge/backend-python-1002',
    apply_url: 'https://jobs.ashbyhq.com/data-forge/backend-python-1002',
    apply_portal: 'ashby',
    source_tags: ['provider:arbeitnow', 'apply_portal:ashby'],
    contents: 'Own API performance and queue reliability.',
  },
  {
    id: 'mock-job-1003',
    provider: 'the_muse',
    provider_job_id: '7619282',
    name: 'Product Designer',
    short_name: 'Product Designer',
    short_description: 'Shape UX flows, prototypes, and research-backed design decisions for recruiting products.',
    company: 'Northwind Studio',
    locations: ['Boston, MA'],
    location_country_code: 'US',
    location_country_name: 'United States',
    levels: ['Entry Level'],
    categories: ['Design'],
    tags: ['Figma', 'UX', 'Research'],
    type: 'Full Time',
    model_type: 'remote',
    work_mode_reason: 'Remote-first team',
    has_remote: true,
    has_hybrid: false,
    is_local_compatible_remote: true,
    local_compatibility_reason: 'No hard location lock',
    location_constraints: { countries: ['US', 'CA'] },
    quality_score: 0.88,
    publication_date: '2026-04-06T13:45:00Z',
    provider_url: 'https://www.themuse.com/jobs/northwind-studio/product-designer',
    job_url: 'https://www.themuse.com/jobs/northwind-studio/product-designer',
    apply_url: 'https://boards.greenhouse.io/northwind/jobs/1003',
    apply_portal: 'greenhouse',
    source_tags: ['provider:the_muse', 'apply_portal:greenhouse'],
    contents: 'Design recruiting workflows and dashboard UX.',
  },
  {
    id: 'mock-job-1004',
    provider: 'arbeitnow',
    provider_job_id: 'data-analyst',
    name: 'Data Analyst',
    short_name: 'Data Analyst',
    short_description: 'Create hiring funnel analytics, reporting, and planning insights with a hybrid analytics team.',
    company: 'Peak Metrics',
    locations: ['Seattle, WA'],
    location_country_code: 'US',
    location_country_name: 'United States',
    levels: ['Mid Level'],
    categories: ['Data Science'],
    tags: ['SQL', 'Tableau', 'Analytics'],
    type: 'Contract',
    model_type: 'hybrid',
    work_mode_reason: 'Hybrid planning cadence',
    has_remote: true,
    has_hybrid: true,
    is_local_compatible_remote: true,
    local_compatibility_reason: 'Remote with occasional office visits',
    location_constraints: { countries: ['US'] },
    quality_score: 0.75,
    publication_date: '2026-03-31T15:15:00Z',
    provider_url: 'https://jobs.lever.co/peak-metrics/1004',
    job_url: 'https://jobs.lever.co/peak-metrics/1004',
    apply_url: 'https://jobs.lever.co/peak-metrics/1004',
    apply_portal: 'lever',
    source_tags: ['provider:arbeitnow', 'apply_portal:lever'],
    contents: 'Create analytics for hiring funnel performance.',
  },
  {
    id: 'mock-job-1005',
    provider: 'the_muse',
    provider_job_id: '7619283',
    name: 'Security Engineer',
    short_name: 'Security Engineer',
    short_description: 'Develop secure defaults, incident tooling, and practical detection workflows for core systems.',
    company: 'ShieldOps',
    locations: ['Chicago, IL'],
    location_country_code: 'US',
    location_country_name: 'United States',
    levels: ['Senior Level'],
    categories: ['IT'],
    tags: ['Security', 'Threat Modeling', 'SIEM'],
    type: 'Full Time',
    model_type: 'hybrid',
    work_mode_reason: 'Incident response rotation',
    has_remote: true,
    has_hybrid: true,
    is_local_compatible_remote: false,
    local_compatibility_reason: '',
    location_constraints: { countries: ['US'] },
    quality_score: 0.83,
    publication_date: '2026-04-01T08:20:00Z',
    provider_url: 'https://www.themuse.com/jobs/shieldops/security-engineer',
    job_url: 'https://www.themuse.com/jobs/shieldops/security-engineer',
    apply_url: 'https://www.themuse.com/jobs/shieldops/security-engineer',
    apply_portal: 'company_site',
    source_tags: ['provider:the_muse'],
    contents: 'Develop secure defaults and incident tooling.',
  },
  {
    id: 'mock-job-1006',
    provider: 'arbeitnow',
    provider_job_id: 'qa-automation-engineer',
    name: 'QA Automation Engineer',
    short_name: 'QA Automation',
    short_description: 'Automate regression coverage and stabilize release quality across a distributed QA organization.',
    company: 'Blue Pine Labs',
    locations: ['Toronto, ON'],
    location_country_code: 'CA',
    location_country_name: 'Canada',
    levels: ['Mid Level'],
    categories: ['Software Engineer'],
    tags: ['Playwright', 'CI', 'Testing'],
    type: 'Full Time',
    model_type: 'remote',
    work_mode_reason: 'Distributed QA team',
    has_remote: true,
    has_hybrid: false,
    is_local_compatible_remote: true,
    local_compatibility_reason: 'Remote-allowed in North America',
    location_constraints: { countries: ['CA', 'US'] },
    quality_score: 0.97,
    publication_date: '2026-04-07T10:05:00Z',
    provider_url: 'https://jobs.workable.com/blue-pine-labs/1006',
    job_url: 'https://jobs.workable.com/blue-pine-labs/1006',
    apply_url: 'https://jobs.workable.com/blue-pine-labs/1006',
    apply_portal: 'workable',
    source_tags: ['provider:arbeitnow', 'apply_portal:workable'],
    contents: 'Automate regression and smoke suites.',
  },
]

let mockFetchInstalled = false

function parseBoolean(value, fallback = false) {
  if (value === undefined || value === null || value === '') return fallback
  const normalized = String(value).trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false
  return fallback
}

function asJson(value) {
  return JSON.parse(JSON.stringify(value))
}

function nowIso() {
  return new Date().toISOString()
}

function normalizeMode(rawMode) {
  const mode = String(rawMode || '').trim().toLowerCase()
  if (mode === 'backend') return 'backend'
  if (mode === 'mock') return 'mock'
  return 'mock'
}

function encodeBase64(value) {
  return btoa(unescape(encodeURIComponent(value)))
}

function makeMockToken(user) {
  const header = { alg: 'HS256', typ: 'JWT' }
  const payload = {
    sub: String(user.id),
    username: user.email || user.username,
    exp: Math.floor(Date.now() / 1000) + 12 * 60 * 60,
    iat: Math.floor(Date.now() / 1000),
  }

  return `${encodeBase64(JSON.stringify(header))}.${encodeBase64(JSON.stringify(payload))}.mock-signature`
}

function isLoopbackHost(hostname) {
  if (!hostname) return false
  return LOOPBACK_HOSTS.has(String(hostname).trim().toLowerCase())
}

function isLoopbackOrigin(origin) {
  try {
    const url = new URL(origin)
    return isLoopbackHost(url.hostname)
  } catch {
    return false
  }
}

export function getFrontendLocalMode() {
  const hostname = typeof window !== 'undefined' ? window.location?.hostname : ''
  const isLoopbackRuntime = isLoopbackHost(hostname)

  // Guardrail: never enable mock mode on non-loopback hosts.
  // This prevents remote environments (dev/beta/prod domains) from silently
  // intercepting API calls when VITE_LOCAL_MODE is misconfigured.
  if (!isLoopbackRuntime) return 'backend'

  const explicit = import.meta.env.VITE_LOCAL_MODE
  if (explicit) return normalizeMode(explicit)

  if (import.meta.env.MODE === 'backend') return 'backend'
  if (import.meta.env.MODE === 'mock') return 'mock'

  // Safe default: only assume mock mode on loopback hosts.
  if (isLoopbackRuntime) return 'mock'

  return 'backend'
}

export function assertSafeLocalModeConfig() {
  const mode = getFrontendLocalMode()
  if (mode !== 'backend') return

  const backendOrigin = String(import.meta.env.VITE_LOCAL_BACKEND_ORIGIN || 'http://localhost:8000').trim()
  const allowRemoteApi = parseBoolean(import.meta.env.VITE_ALLOW_REMOTE_API, false)

  if (!allowRemoteApi && !isLoopbackOrigin(backendOrigin)) {
    throw new Error(
      `[local-mode] Refusing backend mode target '${backendOrigin}'. Use a localhost/127.0.0.1/::1 origin or set VITE_ALLOW_REMOTE_API=true explicitly.`
    )
  }
}

function createDefaultUser(overrides = {}) {
  const defaultEmail = 'localdev@uah.local'
  return {
    id: 1,
    username: defaultEmail,
    email: defaultEmail,
    hashed_password: 'mock-password-hash',
    email_verified: true,
    is_admin: true,
    is_developer: true,
    google_id: null,
    gmail_refresh_token: null,
    gmail_email: null,
    first_name: 'Local',
    last_name: 'Developer',
    phone: '',
    linkedin: '',
    portfolio: '',
    streetAddress: '',
    City: '',
    state: '',
    zip: '',
    degree: '',
    major: '',
    university: '',
    gradYear: '',
    gpa: '',
    yearsExperience: '5',
    currentJobTitle: 'Frontend Engineer',
    currentCompany: 'UAH',
    salaryRange: '',
    preferredLocations: 'Huntsville, AL',
    ...overrides,
  }
}

function createResumeStructuredData(user) {
  return {
    personal_info: {
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
      phone: '(256) 555-0199',
      city: 'Huntsville',
      state: 'AL',
      linkedin: '',
      website: '',
    },
    summary: 'Frontend-focused developer with backend collaboration experience.',
    skills: {
      technical: ['Vue', 'JavaScript', 'Python'],
      languages: ['English'],
      tools: ['Vite', 'Docker', 'Git'],
      soft_skills: ['Communication', 'Problem Solving'],
    },
    education: [
      {
        institution: 'University of Alabama in Huntsville',
        degree: 'B.S.',
        field_of_study: 'Computer Science',
        start_date: '2019-08-15',
        end_date: '2023-05-15',
        gpa: '3.8',
      },
    ],
    work_experience: [
      {
        company: 'UAH Labs',
        title: 'Software Engineer',
        start_date: '2023-06-01',
        end_date: 'Present',
        bullets: ['Built full-stack recruiter workflows', 'Improved page-load and API response stability'],
      },
    ],
    _validation: {
      missing_required: [],
    },
  }
}

function createResume(id, user, overrides = {}) {
  const createdAt = nowIso()
  return syncMockResumeRecord({
    id,
    file_name: `Resume_${id}.pdf`,
    created_at: createdAt,
    updated_at: createdAt,
    parse_method: 'local',
    portal_ready: true,
    has_pdf: true,
    structured_data: createResumeStructuredData(user),
    review_status: '',
    review_draft: null,
    review_updated_at: null,
    ...overrides,
  })
}

function createProfile(user, id = 1, overrides = {}) {
  const createdAt = nowIso()
  return syncMockProfileStorage({
    id,
    name: 'Default',
    is_active: true,
    is_default: true,
    created_at: createdAt,
    updated_at: createdAt,
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    email: user.email || '',
    phone: '',
    linkedin: '',
    portfolio: '',
    street_address: '',
    city: '',
    state: '',
    zip: '',
    summary: '',
    work_auth: '',
    requires_sponsorship: '',
    degree: '',
    major: '',
    university: '',
    grad_year: '',
    gpa: '',
    years_experience: '',
    job_title: '',
    skills_text: '',
    certifications_text: '',
    professional_links_text: '',
    education_history_text: '',
    employment_history_text: '',
    demographic_gender: '',
    demographic_ethnicity: '',
    veteran_status: '',
    disability_status: '',
    california_resident: '',
    ...overrides,
  })
}

function cleanProfileString(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function cleanProfileList(value) {
  return Array.isArray(value)
    ? value.map((item) => cleanProfileString(item)).filter(Boolean)
    : []
}

function splitProfileList(value) {
  return String(value || '')
    .split(/[\n,;]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function splitProfileLines(value) {
  return String(value || '')
    .split(/\r?\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function normalizeCanonicalData(value = {}) {
  const draft = value && typeof value === 'object' ? value : {}
  const personal = draft.personal_info && typeof draft.personal_info === 'object' ? draft.personal_info : {}
  const skills = draft.skills && typeof draft.skills === 'object' ? draft.skills : {}
  const normalizeEntryList = (entries, mapper) => Array.isArray(entries) ? entries.map((entry) => mapper(entry)).filter((entry) => Object.values(entry).some((item) => Array.isArray(item) ? item.length : Boolean(cleanProfileString(item)))) : []

  return {
    personal_info: {
      first_name: cleanProfileString(personal.first_name),
      last_name: cleanProfileString(personal.last_name),
      email: cleanProfileString(personal.email),
      phone: cleanProfileString(personal.phone),
      address: cleanProfileString(personal.address),
      city: cleanProfileString(personal.city),
      state: cleanProfileString(personal.state),
      zip: cleanProfileString(personal.zip),
      linkedin: cleanProfileString(personal.linkedin),
      website: cleanProfileString(personal.website),
    },
    summary: cleanProfileString(draft.summary),
    skills: {
      technical: cleanProfileList(skills.technical),
      languages: cleanProfileList(skills.languages),
      tools: cleanProfileList(skills.tools),
      soft_skills: cleanProfileList(skills.soft_skills),
    },
    education: normalizeEntryList(draft.education, (entry = {}) => ({
      institution: cleanProfileString(entry.institution),
      degree: cleanProfileString(entry.degree),
      field_of_study: cleanProfileString(entry.field_of_study),
      gpa: cleanProfileString(entry.gpa),
      start_date: cleanProfileString(entry.start_date),
      end_date: cleanProfileString(entry.end_date),
      honors: cleanProfileList(entry.honors),
      relevant_coursework: cleanProfileList(entry.relevant_coursework),
    })),
    work_experience: normalizeEntryList(draft.work_experience, (entry = {}) => ({
      company: cleanProfileString(entry.company),
      title: cleanProfileString(entry.title),
      location: cleanProfileString(entry.location),
      start_date: cleanProfileString(entry.start_date),
      end_date: cleanProfileString(entry.end_date),
      is_current: Boolean(entry.is_current || String(entry.end_date || '').toLowerCase() === 'present'),
      bullets: cleanProfileList(entry.bullets),
    })),
    projects: normalizeEntryList(draft.projects, (entry = {}) => ({
      name: cleanProfileString(entry.name),
      description: cleanProfileString(entry.description),
      date: cleanProfileString(entry.date),
      technologies: cleanProfileList(entry.technologies),
    })),
    certifications: normalizeEntryList(draft.certifications, (entry = {}) => ({
      name: cleanProfileString(typeof entry === 'string' ? entry : entry.name),
      issuer: cleanProfileString(entry?.issuer),
      date: cleanProfileString(entry?.date),
    })),
    awards: cleanProfileList(draft.awards),
    activities: cleanProfileList(draft.activities),
    volunteer: cleanProfileList(draft.volunteer),
  }
}

function deriveCanonicalFromProfile(profile = {}) {
  const education = []
  if (cleanProfileString(profile.university) || cleanProfileString(profile.degree) || cleanProfileString(profile.major)) {
    education.push({
      institution: cleanProfileString(profile.university),
      degree: cleanProfileString(profile.degree),
      field_of_study: cleanProfileString(profile.major),
      gpa: cleanProfileString(profile.gpa),
      end_date: cleanProfileString(profile.grad_year),
    })
  }
  splitProfileLines(profile.education_history_text).forEach((line) => {
    const parts = line.split('|').map((item) => item.trim())
    education.push({
      institution: cleanProfileString(parts[0]),
      degree: cleanProfileString(parts[1]),
      field_of_study: cleanProfileString(parts[2]),
      start_date: cleanProfileString(parts[3]),
      end_date: cleanProfileString(parts[4]),
      gpa: cleanProfileString(parts[5]),
    })
  })

  const workExperience = []
  if (cleanProfileString(profile.job_title)) {
    workExperience.push({ title: cleanProfileString(profile.job_title) })
  }
  splitProfileLines(profile.employment_history_text).forEach((line) => {
    const parts = line.split('|').map((item) => item.trim())
    workExperience.push({
      company: cleanProfileString(parts[0]),
      title: cleanProfileString(parts[1]),
      location: cleanProfileString(parts[2]),
      start_date: cleanProfileString(parts[3]),
      end_date: cleanProfileString(parts[4]),
      is_current: String(parts[4] || '').toLowerCase() === 'present',
    })
  })

  return normalizeCanonicalData({
    personal_info: {
      first_name: profile.first_name,
      last_name: profile.last_name,
      email: profile.email,
      phone: profile.phone,
      address: profile.street_address,
      city: profile.city,
      state: profile.state,
      zip: profile.zip,
      linkedin: profile.linkedin,
      website: profile.portfolio,
    },
    summary: profile.summary,
    skills: { technical: splitProfileList(profile.skills_text) },
    education,
    work_experience: workExperience,
    certifications: splitProfileLines(profile.certifications_text).map((name) => ({ name })),
    awards: [],
    activities: [],
    volunteer: [],
  })
}

function flattenCanonicalData(canonical) {
  const normalized = normalizeCanonicalData(canonical)
  const tokens = {}
  Object.entries(normalized.personal_info || {}).forEach(([key, value]) => {
    if (cleanProfileString(value)) tokens[`personal_info.${key}`] = value
  })
  if (cleanProfileString(normalized.summary)) tokens.summary = normalized.summary
  ;['education', 'work_experience', 'projects', 'certifications'].forEach((sectionKey) => {
    ;(normalized[sectionKey] || []).forEach((entry, index) => {
      Object.entries(entry || {}).forEach(([key, value]) => {
        if (Array.isArray(value) && value.length) {
          tokens[`${sectionKey}[${index}].${key}`] = value.join(key === 'bullets' ? '\n' : ', ')
        } else if (!Array.isArray(value) && cleanProfileString(String(value || ''))) {
          tokens[`${sectionKey}[${index}].${key}`] = value
        }
      })
    })
  })
  Object.entries(normalized.skills || {}).forEach(([key, value]) => {
    if (Array.isArray(value) && value.length) tokens[`skills.${key}`] = value.join(', ')
  })
  ;['awards', 'activities', 'volunteer'].forEach((key) => {
    if (normalized[key]?.length) tokens[key] = normalized[key].join('\n')
  })
  return tokens
}

function deriveProfileFieldsFromCanonical(canonical, existing = {}) {
  const normalized = normalizeCanonicalData(canonical)
  const primaryEducation = normalized.education[0] || {}
  const extraEducation = normalized.education.slice(1)
  const primaryWork = normalized.work_experience[0] || {}
  const extraWork = normalized.work_experience.slice(primaryWork.title ? 1 : 0)
  const allSkills = [
    ...(normalized.skills.technical || []),
    ...(normalized.skills.languages || []),
    ...(normalized.skills.tools || []),
    ...(normalized.skills.soft_skills || []),
  ].filter(Boolean)

  return {
    first_name: cleanProfileString(normalized.personal_info.first_name),
    last_name: cleanProfileString(normalized.personal_info.last_name),
    email: cleanProfileString(normalized.personal_info.email),
    phone: cleanProfileString(normalized.personal_info.phone),
    linkedin: cleanProfileString(normalized.personal_info.linkedin),
    portfolio: cleanProfileString(normalized.personal_info.website),
    street_address: cleanProfileString(normalized.personal_info.address),
    city: cleanProfileString(normalized.personal_info.city),
    state: cleanProfileString(normalized.personal_info.state),
    zip: cleanProfileString(normalized.personal_info.zip),
    summary: cleanProfileString(normalized.summary),
    degree: cleanProfileString(primaryEducation.degree),
    major: cleanProfileString(primaryEducation.field_of_study),
    university: cleanProfileString(primaryEducation.institution),
    grad_year: cleanProfileString(primaryEducation.end_date),
    gpa: cleanProfileString(primaryEducation.gpa),
    job_title: cleanProfileString(primaryWork.title) || cleanProfileString(existing.job_title),
    years_experience: cleanProfileString(existing.years_experience),
    skills_text: allSkills.join(', '),
    certifications_text: normalized.certifications.map((item) => cleanProfileString(item.name)).filter(Boolean).join('\n'),
    professional_links_text: cleanProfileString(existing.professional_links_text),
    education_history_text: extraEducation.map((item) => [item.institution, item.degree, item.field_of_study, item.start_date, item.end_date, item.gpa].map((part) => cleanProfileString(part)).join(' | ')).filter(Boolean).join('\n'),
    employment_history_text: extraWork.map((item) => [item.company, item.title, item.location, item.start_date, item.end_date || (item.is_current ? 'Present' : '')].map((part) => cleanProfileString(part)).join(' | ')).filter(Boolean).join('\n'),
  }
}

function syncMockProfileStorage(profile = {}) {
  const canonical = profile.canonical_data ? normalizeCanonicalData(profile.canonical_data) : deriveCanonicalFromProfile(profile)
  return {
    ...profile,
    ...deriveProfileFieldsFromCanonical(canonical, profile),
    canonical_data: canonical,
    token_map: flattenCanonicalData(canonical),
    updated_at: profile.updated_at || profile.created_at || nowIso(),
  }
}

function syncMockResumeRecord(resume = {}) {
  return {
    ...resume,
    review_status: cleanProfileString(resume.review_status) || '',
    review_draft: resume.review_draft && typeof resume.review_draft === 'object' ? resume.review_draft : null,
    review_updated_at: resume.review_updated_at || null,
    has_review_draft: Boolean(resume.review_draft && typeof resume.review_draft === 'object'),
  }
}

function generateMockReviewConflicts(existingCanonical, incomingCanonical) {
  const existingTokens = flattenCanonicalData(existingCanonical)
  const incomingTokens = flattenCanonicalData(incomingCanonical)
  return Object.entries(incomingTokens).reduce((accumulator, [path, incomingValue]) => {
    const existingValue = existingTokens[path]
    if (!existingValue || !incomingValue || existingValue === incomingValue) return accumulator
    accumulator.push({
      id: path,
      path,
      label: path.replace(/^personal_info\./, '').replace(/_/g, ' ').replace(/\[(\d+)\]/g, (_, number) => ` #${Number(number) + 1}`).replace(/\./g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
      existing_value: existingValue,
      incoming_value: incomingValue,
      resolution: 'existing',
    })
    return accumulator
  }, []).sort((left, right) => left.label.localeCompare(right.label))
}

function mergeMockReviewIntoProfile(existingCanonical, incomingCanonical, conflictResolutions = {}) {
  const existing = normalizeCanonicalData(existingCanonical)
  const incoming = normalizeCanonicalData(incomingCanonical)
  const existingTokens = flattenCanonicalData(existing)
  const incomingTokens = flattenCanonicalData(incoming)
  const conflicts = generateMockReviewConflicts(existing, incoming)
  const conflictPaths = new Set(conflicts.map((item) => item.path))
  const mergedTokens = { ...existingTokens }

  Object.entries(incomingTokens).forEach(([path, value]) => {
    if (!mergedTokens[path]) {
      mergedTokens[path] = value
      return
    }
    if (conflictPaths.has(path) && conflictResolutions[path] !== 'incoming') return
    mergedTokens[path] = value
  })

  const merged = normalizeCanonicalData({
    personal_info: {
      first_name: mergedTokens['personal_info.first_name'],
      last_name: mergedTokens['personal_info.last_name'],
      email: mergedTokens['personal_info.email'],
      phone: mergedTokens['personal_info.phone'],
      address: mergedTokens['personal_info.address'],
      city: mergedTokens['personal_info.city'],
      state: mergedTokens['personal_info.state'],
      zip: mergedTokens['personal_info.zip'],
      linkedin: mergedTokens['personal_info.linkedin'],
      website: mergedTokens['personal_info.website'],
    },
    summary: mergedTokens.summary,
    skills: {
      technical: [...(existing.skills.technical || []), ...(incoming.skills.technical || [])],
      languages: [...(existing.skills.languages || []), ...(incoming.skills.languages || [])],
      tools: [...(existing.skills.tools || []), ...(incoming.skills.tools || [])],
      soft_skills: [...(existing.skills.soft_skills || []), ...(incoming.skills.soft_skills || [])],
    },
    education: [...existing.education, ...incoming.education],
    work_experience: [...existing.work_experience, ...incoming.work_experience],
    projects: [...existing.projects, ...incoming.projects],
    certifications: [...existing.certifications, ...incoming.certifications],
    awards: [...existing.awards, ...incoming.awards],
    activities: [...existing.activities, ...incoming.activities],
    volunteer: [...existing.volunteer, ...incoming.volunteer],
  })

  return { merged, conflicts }
}

function createDefaultState() {
  const user = createDefaultUser()
  return {
    version: 1,
    user,
    resumes: [
      createResume(1, user),
      createResume(2, user, {
        file_name: 'Resume_Draft.pdf',
        parse_method: null,
        portal_ready: false,
        structured_data: {
          ...createResumeStructuredData(user),
          _validation: {
            missing_required: ['work_experience.title', 'education.degree'],
          },
        },
      }),
    ],
    profiles: [createProfile(user)],
    parseJobs: {},
    nextIds: {
      resume: 3,
      profile: 2,
      parseJob: 100,
    },
  }
}

function ensureArray(value, fallback = []) {
  return Array.isArray(value) ? value : fallback
}

function ensureStateShape(state) {
  const safe = state && typeof state === 'object' ? state : createDefaultState()
  safe.user = safe.user && typeof safe.user === 'object' ? { ...createDefaultUser(), ...safe.user } : createDefaultUser()
  safe.resumes = ensureArray(safe.resumes, []).map((resume) => syncMockResumeRecord(resume))
  safe.profiles = ensureArray(safe.profiles, []).map((profile) => syncMockProfileStorage(profile))
  safe.parseJobs = safe.parseJobs && typeof safe.parseJobs === 'object' ? safe.parseJobs : {}
  safe.nextIds = safe.nextIds && typeof safe.nextIds === 'object' ? safe.nextIds : { resume: 1, profile: 1, parseJob: 1 }
  safe.nextIds.resume = Number(safe.nextIds.resume || safe.resumes.length + 1)
  safe.nextIds.profile = Number(safe.nextIds.profile || safe.profiles.length + 1)
  safe.nextIds.parseJob = Number(safe.nextIds.parseJob || 100)

  if (!safe.profiles.length) {
    safe.profiles = [createProfile(safe.user)]
    safe.nextIds.profile = Math.max(safe.nextIds.profile, 2)
  }

  if (!safe.resumes.length) {
    safe.resumes = [createResume(1, safe.user)]
    safe.nextIds.resume = Math.max(safe.nextIds.resume, 2)
  }

  return safe
}

function loadState() {
  try {
    const raw = localStorage.getItem(MOCK_STATE_KEY)
    if (!raw) return createDefaultState()
    return ensureStateShape(JSON.parse(raw))
  } catch {
    return createDefaultState()
  }
}

function saveState(state) {
  localStorage.setItem(MOCK_STATE_KEY, JSON.stringify(state))
}

function getAuthUserFromStorage(state) {
  const token = getAccessToken()
  if (!token) return null

  const currentUser = getCurrentUser()
  if (currentUser) return currentUser

  return state.user || null
}

function setAuthStorage(user) {
  const token = makeMockToken(user)
  setAuth({ access_token: token, user })
}

function maybeBootstrapAutoLogin(state) {
  const autoLogin = parseBoolean(import.meta.env.VITE_LOCAL_AUTO_LOGIN, false)
  if (!autoLogin) return

  if (!getAccessToken()) {
    setAuthStorage(state.user)
  }
}

function toJsonResponse(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
  })
}

function toPdfResponse() {
  const pdfBody = `%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\nendobj\n4 0 obj\n<< /Length 55 >>\nstream\nBT /F1 18 Tf 72 720 Td (UAH Local Mock Resume Preview) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000116 00000 n \n0000000222 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n328\n%%EOF\n`

  return new Response(pdfBody, {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Cache-Control': 'no-store',
    },
  })
}

function parseInteger(value, fallback) {
  const n = Number.parseInt(String(value || ''), 10)
  return Number.isFinite(n) ? n : fallback
}

function normalizeText(value) {
  return String(value || '').trim()
}

function normalizeTextLower(value) {
  return normalizeText(value).toLowerCase()
}

function normalizeWhitespace(value) {
  return normalizeText(value).replace(/\s+/g, ' ')
}

function normalizeIsoDate(value) {
  const raw = normalizeText(value)
  if (!raw) return ''
  const parsed = new Date(raw)
  if (Number.isNaN(parsed.getTime())) return ''
  return parsed.toISOString()
}

function simpleHash(value) {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i)
    hash |= 0
  }
  return `mock-${Math.abs(hash)}`
}

function normalizeMockLevelValue(value) {
  const normalized = normalizeTextLower(value)
  if (!normalized) return ''
  return LEVEL_VALUE_ALIASES[normalized] || normalized
}

function labelMockLevelValue(value) {
  const normalized = normalizeMockLevelValue(value)
  if (!normalized) return ''
  return LEVEL_LABELS[normalized] || normalized.split(' ').map((part) => {
    if (!part) return part
    return part.charAt(0).toUpperCase() + part.slice(1)
  }).join(' ')
}

function getMockDisplayEnabledProviders() {
  return Object.values(PROVIDER_ATTRIBUTION_FIXTURES)
    .filter((provider) => provider?.display_enabled === true)
    .map((provider) => normalizeTextLower(provider.provider))
    .filter(Boolean)
}

function getMockSearchableJobs() {
  const enabledProviders = new Set(getMockDisplayEnabledProviders())
  return JOB_FIXTURES.filter((job) => enabledProviders.has(normalizeTextLower(job.provider)))
}

function getMockCountryName(countryCode) {
  const normalized = normalizeTextUpper(countryCode)
  if (!normalized) return ''

  const fixtureMatch = COUNTRY_FIXTURES.find((country) => normalizeTextUpper(country.code) === normalized)
  if (fixtureMatch?.name) return fixtureMatch.name

  const cityMatch = allCities().find((city) => normalizeTextUpper(city.country_code) === normalized)
  if (cityMatch?.country) return cityMatch.country

  return normalized
}

function getMockJobCountryCode(job) {
  const normalized = normalizeTextUpper(job?.location_country_code)
  if (normalized) return normalized

  const constrained = normalizeTextUpper(job?.location_constraints?.countries?.[0])
  if (constrained) return constrained

  const location = normalizeTextLower(job?.locations?.[0])
  const cityMatch = allCities().find((city) => {
    const cityName = normalizeTextLower(cityToMuseLocationName(city))
    return cityName && location && (location.includes(cityName) || cityName.includes(location))
  })
  return normalizeTextUpper(cityMatch?.country_code)
}

function getMockJobCountryName(job) {
  const normalized = normalizeWhitespace(job?.location_country_name)
  if (normalized) return normalized
  return getMockCountryName(getMockJobCountryCode(job))
}

function buildMockCategoryValues() {
  const counts = new Map()

  for (const group of CATEGORY_GROUPS) {
    for (const rawValue of group.muse_categories || []) {
      const value = normalizeWhitespace(rawValue)
      if (!value) continue
      if (!counts.has(value)) counts.set(value, 0)
    }
  }

  for (const job of getMockSearchableJobs()) {
    for (const rawValue of job.categories || []) {
      const value = normalizeWhitespace(rawValue)
      if (!value) continue
      counts.set(value, Number(counts.get(value) || 0) + 1)
    }
  }

  return [...counts.entries()]
    .sort((a, b) => {
      if (a[1] !== b[1]) return b[1] - a[1]
      return a[0].localeCompare(b[0])
    })
    .map(([value, observed_count]) => ({ value, observed_count }))
}

function buildMockLevelValues() {
  const counts = new Map()

  for (const value of Object.keys(LEVEL_LABELS)) {
    counts.set(value, 0)
  }

  for (const job of getMockSearchableJobs()) {
    for (const rawValue of job.levels || []) {
      const value = normalizeMockLevelValue(rawValue)
      if (!value) continue
      counts.set(value, Number(counts.get(value) || 0) + 1)
    }
  }

  return [...counts.entries()]
    .sort((a, b) => {
      if (a[1] !== b[1]) return b[1] - a[1]
      return labelMockLevelValue(a[0]).localeCompare(labelMockLevelValue(b[0]))
    })
    .map(([value, observed_count]) => ({
      value,
      label: labelMockLevelValue(value),
      observed_count,
    }))
}

function buildMockCountryValues() {
  const counts = new Map()

  for (const job of getMockSearchableJobs()) {
    const code = getMockJobCountryCode(job)
    if (!code) continue
    const name = getMockJobCountryName(job) || code
    const current = counts.get(code) || { code, name, observed_count: 0 }
    current.observed_count += 1
    if (!current.name && name) current.name = name
    counts.set(code, current)
  }

  return [...counts.values()].sort((a, b) => {
    if (a.observed_count !== b.observed_count) return b.observed_count - a.observed_count
    return a.name.localeCompare(b.name)
  })
}

function buildMockProviderValues() {
  const observedCounts = new Map()
  for (const job of getMockSearchableJobs()) {
    const provider = normalizeTextLower(job.provider)
    if (!provider) continue
    observedCounts.set(provider, Number(observedCounts.get(provider) || 0) + 1)
  }

  return getMockDisplayEnabledProviders()
    .map((provider) => {
      const detail = PROVIDER_ATTRIBUTION_FIXTURES[provider] || {}
      const label = normalizeWhitespace(detail?.attribution?.label || provider)
      return {
        value: provider,
        label,
        observed_count: Number(observedCounts.get(provider) || 0),
        display_enabled: true,
      }
    })
    .sort((a, b) => {
      if (a.observed_count !== b.observed_count) return b.observed_count - a.observed_count
      return a.label.localeCompare(b.label)
    })
}

function buildMockFilterMetadata() {
  const categoryValues = buildMockCategoryValues()
  const levelValues = buildMockLevelValues()
  const countryValues = buildMockCountryValues()
  const providerValues = buildMockProviderValues()
  const payload = {
    category_groups: CATEGORY_GROUPS.map((group) => ({
      key: group.key,
      name: group.name,
      muse_categories: [...group.muse_categories],
    })),
    category_aliases: { ...CATEGORY_ALIAS },
    category_values: categoryValues,
    level_values: levelValues,
    country_values: countryValues,
    provider_values: providerValues,
    levels: levelValues.map((item) => item.label),
    location_param_cap: MOCK_LOCATION_PARAM_CAP,
  }
  const core = JSON.stringify(payload)
  return {
    ...payload,
    metadata_version: 'jobs-filter-v2',
    metadata_hash: simpleHash(core),
  }
}

function expandCategoriesForMock(values) {
  const expanded = []
  const seen = new Set()

  for (const rawValue of values || []) {
    const value = normalizeText(rawValue)
    if (!value) continue

    const lower = value.toLowerCase()
    const aliased = CATEGORY_ALIAS[lower] || value
    const group = CATEGORY_GROUP_BY_NAME[normalizeTextLower(aliased)]
    const candidates = group ? group.muse_categories : [value]

    for (const candidate of candidates) {
      const key = normalizeTextLower(candidate)
      if (!key || seen.has(key)) continue
      seen.add(key)
      expanded.push(candidate)
    }
  }

  return expanded
}

function parsePostedAfter(rawValue) {
  const iso = normalizeIsoDate(rawValue)
  if (!iso) return null
  return new Date(iso)
}

function matchesPostedAfter(job, postedAfter) {
  if (!postedAfter) return true
  const publicationDate = new Date(job.publication_date || '')
  if (Number.isNaN(publicationDate.getTime())) return false
  return publicationDate >= postedAfter
}

function getPublicationTimestamp(job) {
  const publicationDate = new Date(job?.publication_date || '')
  return Number.isNaN(publicationDate.getTime()) ? 0 : publicationDate.getTime()
}

function sortMockJobs(jobs, sortBy) {
  const normalizedSort = normalizeTextLower(sortBy) || 'date_desc'
  const sorted = [...jobs]

  sorted.sort((a, b) => {
    if (normalizedSort === 'quality_desc') {
      const qualityDelta = Number(b?.quality_score || 0) - Number(a?.quality_score || 0)
      if (qualityDelta !== 0) return qualityDelta
      return getPublicationTimestamp(b) - getPublicationTimestamp(a)
    }

    if (normalizedSort === 'date_asc') {
      const publishedDelta = getPublicationTimestamp(a) - getPublicationTimestamp(b)
      if (publishedDelta !== 0) return publishedDelta
      return Number(b?.quality_score || 0) - Number(a?.quality_score || 0)
    }

    const publishedDelta = getPublicationTimestamp(b) - getPublicationTimestamp(a)
    if (publishedDelta !== 0) return publishedDelta
    return Number(b?.quality_score || 0) - Number(a?.quality_score || 0)
  })

  return sorted
}

function haversineMiles(lat1, lon1, lat2, lon2) {
  const toRad = (deg) => (deg * Math.PI) / 180
  const earthRadiusMiles = 3958.7613

  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2

  return 2 * earthRadiusMiles * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function allCities() {
  return Object.values(CITY_FIXTURES).flat()
}

function coerceMethod(method) {
  return String(method || 'GET').toUpperCase()
}

function publicApiPath(pathname) {
  return [
    '/api/auth/login',
    '/api/auth/register',
    '/api/account/forgot-password',
    '/api/account/reset-password',
    '/api/account/verify-email',
    '/api/diagnostics',
    '/api/health',
    '/api/',
    '/api',
    '/docs',
    '/openapi.json',
  ].includes(pathname)
}

function requireAuth(pathname, state) {
  if (publicApiPath(pathname)) return { ok: true, user: null }

  const user = getAuthUserFromStorage(state)
  if (!user) {
    return {
      ok: false,
      response: toJsonResponse({ detail: 'Not authenticated' }, 401),
    }
  }

  return { ok: true, user }
}

function buildQueueSnapshot(state, focusMethod = 'local', includeGlobalQueue = true) {
  const jobs = Object.values(state.parseJobs || {})
  const activeStatuses = new Set(['queued', 'parsing', 'validating'])
  const activeJobs = jobs.filter((job) => activeStatuses.has(job.status))

  const queueDepthByMethod = {
    local: 0,
    cloud: 0,
    rules: 0,
  }

  for (const job of activeJobs) {
    const method = normalizeTextLower(job.method) || 'local'
    if (method in queueDepthByMethod) {
      queueDepthByMethod[method] += 1
    } else {
      queueDepthByMethod.local += 1
    }
  }

  const latest = activeJobs[0] || null
  const entries = activeJobs.map((job, index) => ({
    job_id: job.job_id,
    method: job.method,
    status: job.status,
    user_display: 'Local Developer',
    queue_position: index + 1,
    queue_total: activeJobs.length,
    created_at: job.created_at,
  }))
  const localAvailable = parseBoolean(import.meta.env.VITE_LOCAL_MOCK_LOCAL_AI_AVAILABLE, true)

  const snapshot = {
    can_view_global: true,
    queue_depth: activeJobs.length,
    queue_depth_total: activeJobs.length,
    queue_depth_by_method: queueDepthByMethod,
    current_user: {
      active_job_position: latest ? 1 : null,
      active_job_total: latest ? activeJobs.length : null,
      focus_method: normalizeTextLower(focusMethod) || 'local',
      latest_active_job_status: latest?.status || null,
      latest_active_job_method: latest?.method || null,
    },
    global_metrics: {
      load_total: state.resumes.length,
      active_total: activeJobs.length,
    },
    worker_status: {
      mode: 'mock',
    },
    pipeline_availability: {
      local: {
        available: localAvailable,
        message: localAvailable ? null : 'Local AI is unavailable right now.',
      },
      cloud: {
        available: true,
      },
      rules: {
        available: true,
      },
    },
    local_queue_note: 'Queue metrics are simulated in local mock mode.',
    cloud_behavior: {
      description: 'Cloud parsing behavior is emulated for UI renderability.',
    },
  }

  if (includeGlobalQueue) {
    snapshot.global_queue = {
      active_count: activeJobs.length,
      entries,
    }
  }

  return snapshot
}

function finalizeResumeParse(state, job) {
  const resumeIndex = state.resumes.findIndex((item) => String(item.id) === String(job.resume_id))
  if (resumeIndex < 0) return

  const resume = state.resumes[resumeIndex]
  const updated = {
    ...resume,
    parse_method: job.method,
    portal_ready: true,
    has_pdf: true,
  }

  const validation = {
    ...(updated.structured_data?._validation || {}),
    missing_required: [],
  }

  updated.structured_data = {
    ...(updated.structured_data || createResumeStructuredData(state.user)),
    _validation: validation,
  }

  updated.review_status = 'pending'
  updated.review_draft = updated.structured_data
  updated.review_updated_at = nowIso()
  updated.updated_at = nowIso()
  state.resumes[resumeIndex] = syncMockResumeRecord(updated)
}

function advanceParseJobState(state, job) {
  if (!job || ['success', 'failed', 'cancelled'].includes(job.status)) return job

  job.poll_count = Number(job.poll_count || 0) + 1
  if (job.poll_count <= 1) {
    job.status = 'queued'
    job.progress_stage = 'Queued'
  } else if (job.poll_count === 2) {
    job.status = 'parsing'
    job.progress_stage = 'Parsing'
  } else if (job.poll_count === 3) {
    job.status = 'validating'
    job.progress_stage = 'Validating'
  } else {
    job.status = 'success'
    job.progress_stage = 'Completed'
    job.result_summary = {
      portal_ready: true,
      missing_required: [],
    }
    finalizeResumeParse(state, job)
  }

  job.updated_at = nowIso()
  return job
}

function makeDiagnosticsPayload() {
  const localAvailable = parseBoolean(import.meta.env.VITE_LOCAL_MOCK_LOCAL_AI_AVAILABLE, true)
  return {
    overall: 'healthy',
    services: {
      backend: {
        name: 'UAH Local Mock API',
        version: 'mock-1.0.0',
        framework: 'Mock Runtime',
        python_version: 'n/a',
        platform: 'Browser',
        pid: 0,
        host: 'mock://frontend',
        status: 'healthy',
      },
      database: {
        status: 'healthy',
        postgres_version: 'mock-15',
        database_name: 'uah_local_mock',
        user: 'localdev',
        size: 'N/A',
        public_tables: 12,
        latency_ms: 1,
        host: 'localhost',
        port: 5432,
        error: null,
      },
      network: {
        status: 'healthy',
        dns_resolution: {
          localhost: { resolved: true, ip: '127.0.0.1' },
          'api.local': { resolved: true, ip: '127.0.0.1' },
        },
      },
      parse_methods: {
        status: localAvailable ? 'healthy' : 'degraded',
        methods: {
          cloud: {
            available: true,
            status: 'healthy',
            message: 'Cloud AI parsing is available.',
          },
          local: {
            available: localAvailable,
            status: localAvailable ? 'healthy' : 'degraded',
            message: localAvailable ? 'Local AI parsing is available.' : 'Local AI is unavailable right now.',
          },
          rules: {
            available: true,
            status: 'healthy',
            message: 'Deterministic rules parsing is available.',
          },
        },
      },
      job_board: {
        status: 'healthy',
        counts: {
          total_jobs: JOB_FIXTURES.length,
          active_jobs: JOB_FIXTURES.length,
          inactive_jobs: 0,
          bad_provider_urls: 0,
          bad_apply_urls: 0,
          stale_jobs: 1,
          active_hashed_jobs: 2,
          active_null_hash_jobs: Math.max(JOB_FIXTURES.length - 2, 0),
        },
        dedup: {
          active_collision_count: 0,
        },
        display_enabled_providers: ['the_muse', 'arbeitnow'],
        latest_sync: {
          id: 'mock-sync-1',
          provider: 'the_muse',
          category: 'sales and marketing',
          started_at: nowIso(),
          completed_at: nowIso(),
          pages_fetched: 2,
          jobs_found: 40,
          jobs_new: 4,
          jobs_updated: 12,
          jobs_deduplicated: 1,
          requests_used: 2,
          stopped_reason: 'threshold_hit',
          error_message: null,
        },
        endpoints: {
          '/api/jobs/filter-metadata': { status: 'healthy', latency_ms: 1.2, metadata_version: 'jobs-filter-v2' },
          '/api/providers/attribution': { status: 'healthy', latency_ms: 1.4, provider_count: Object.keys(PROVIDER_ATTRIBUTION_FIXTURES).length },
          '/api/jobs/search': { status: 'healthy', latency_ms: 2.1, sample_total_jobs: JOB_FIXTURES.length },
        },
      },
    },
  }
}

function toSearchParamsFromObject(raw = {}) {
  const params = new URLSearchParams()
  Object.entries(raw || {}).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item !== undefined && item !== null && item !== '') params.append(key, String(item))
      })
      return
    }
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  })
  return params
}

function buildMockJobsSearchPayload(searchParams) {
  const page = Math.max(1, parseInteger(searchParams.get('page'), 1))
  const pageSize = Math.max(1, Math.min(50, parseInteger(searchParams.get('page_size'), 10)))
  const locationSelection = buildMockLocationSelection(searchParams)
  const selectedLocations = locationSelection.selectedLocations
  const droppedLocations = locationSelection.droppedLocations
  const locationParamsTruncated = locationSelection.locationParamsTruncated
  const searchableJobs = getMockSearchableJobs()

  const filteredResult = applyJobSearchFilters(searchableJobs, searchParams, selectedLocations)
  const filtered = filteredResult.jobs
  const diagnostics = filteredResult.diagnostics || {}
  const totalJobs = filtered.length
  const totalPages = Math.max(1, Math.ceil(totalJobs / pageSize))
  const start = (page - 1) * pageSize
  const jobs = filtered.slice(start, start + pageSize)
  const keywordQuery = normalizeTextLower(searchParams.get('q'))
  const postedAfter = normalizeIsoDate(searchParams.get('posted_after'))
  const metadata = buildMockFilterMetadata()

  return {
    jobs,
    total_jobs: totalJobs,
    total_jobs_estimated: totalJobs,
    total_pages: totalPages,
    total_pages_estimated: totalPages,
    totals_are_estimated: false,
    has_next_page: page < totalPages,
    total_estimate_strategy: 'exact-mock',
    guardrail_stop_reason: '',
    source_pages_scanned: 1,
    filtered_out_count: Number(diagnostics.filteredOutCount || 0),
    requested_location_count: locationSelection.requestedLocationCount,
    used_location_count: selectedLocations.length,
    location_params_used: selectedLocations.length,
    location_params_truncated: locationParamsTruncated,
    dropped_location_count: droppedLocations.length,
    dropped_locations_sample: droppedLocations.slice(0, 12),
    location_mode: locationSelection.mode,
    location_country_code: locationSelection.countryCode,
    has_next_page_possible_raw: page < totalPages,
    has_more_source_pages: page < totalPages,
    source_page_count: totalPages,
    window_start_page: page,
    window_size: 1,
    dropped_invalid_url_count: 0,
    url_validation_checked_count: 0,
    url_validation_cache_hit_count: 0,
    location_relaxed_fallback: false,
    location_selection_strategy: locationSelection.strategy,
    canonicalized_location_count: selectedLocations.length,
    transformed_location_count: 0,
    unmatched_location_count: 0,
    strict_state_blocked_count: 0,
    selected_state_diversity_count: new Set(
      selectedLocations
        .map((location) => {
          const match = String(location || '').match(/,\s*([A-Z]{2})(?:\s*,|\s*$)/)
          return match ? match[1] : ''
        })
        .filter(Boolean)
    ).size,
    accepted_by_concrete_location: Number(diagnostics.acceptedByConcreteLocation || 0),
    accepted_by_remote_override: Number(diagnostics.acceptedByRemoteOverride || 0),
    accepted_by_hybrid_override: Number(diagnostics.acceptedByHybridOverride || 0),
    accepted_by_constraint_overlap: Number(diagnostics.acceptedByConstraintOverlap || 0),
    constraint_parse_high_confidence: Number(diagnostics.constraintParseHighConfidence || 0),
    constraint_parse_medium_confidence: Number(diagnostics.constraintParseMediumConfidence || 0),
    constraint_parse_low_confidence: Number(diagnostics.constraintParseLowConfidence || 0),
    constraint_policy_remote_off: 'allow-if-overlap',
    constraint_compatibility_enabled: true,
    constraint_filter_min_confidence: 'high',
    adaptive_chase_enabled: false,
    adaptive_chase_extra_pages: 0,
    effective_max_pages: 1,
    effective_min_filtered_ratio: 0,
    requested_locations_sample: locationSelection.requestedLocationsSample,
    selected_locations_sample: locationSelection.selectedLocationsSample,
    keyword_query: keywordQuery,
    posted_after: postedAfter,
    jobs_filter_metadata_version: metadata.metadata_version,
    jobs_filter_metadata_hash: metadata.metadata_hash,
    cache_hit: false,
  }
}

function makeMockJobsDebugOverview() {
  return {
    providers: {
      statuses: Object.values(PROVIDER_ATTRIBUTION_FIXTURES).map((provider) => asJson(provider)),
      display_enabled: ['the_muse', 'arbeitnow'],
      ingest_enabled: ['the_muse', 'arbeitnow'],
      scheduled_enabled: ['the_muse', 'arbeitnow'],
    },
    recent_syncs: [
      {
        id: 'mock-sync-1',
        provider: 'the_muse',
        category: 'sales and marketing',
        started_at: nowIso(),
        completed_at: nowIso(),
        pages_fetched: 2,
        jobs_found: 40,
        jobs_new: 4,
        jobs_updated: 12,
        jobs_deduplicated: 1,
        requests_used: 2,
        stopped_reason: 'threshold_hit',
        error_message: null,
      },
      {
        id: 'mock-sync-2',
        provider: 'arbeitnow',
        category: null,
        started_at: nowIso(),
        completed_at: nowIso(),
        pages_fetched: 1,
        jobs_found: 24,
        jobs_new: 2,
        jobs_updated: 8,
        jobs_deduplicated: 0,
        requests_used: 1,
        stopped_reason: 'completed',
        error_message: null,
      },
    ],
    quota_usage: [
      { provider: 'the_muse', hour_bucket: nowIso(), request_count: 2 },
      { provider: 'arbeitnow', hour_bucket: nowIso(), request_count: 1 },
    ],
    database: {
      counts: makeDiagnosticsPayload().services.job_board.counts,
      by_provider: [
        { value: 'the_muse', count: 3 },
        { value: 'arbeitnow', count: 3 },
      ],
      by_display_tier: [{ value: 'active', count: JOB_FIXTURES.length }],
      by_staleness_status: [{ value: 'fresh', count: JOB_FIXTURES.length - 1 }, { value: 'aging', count: 1 }],
      by_provider_url_status: [{ value: 'unknown', count: JOB_FIXTURES.length }],
      by_apply_url_status: [{ value: 'unknown', count: 2 }, { value: 'good', count: JOB_FIXTURES.length - 2 }],
      dedup: {
        active_collision_count: 0,
        collision_samples: [],
      },
    },
  }
}

function makeMockJobsDebugInsights() {
  const samples = JOB_FIXTURES.map((job, index) => ({
    id: job.id,
    provider: job.provider,
    provider_job_id: job.provider_job_id,
    title: job.name,
    company: job.company,
    location: job.locations?.[0] || '',
    is_active: true,
    is_remote: job.has_remote === true,
    display_tier: 'active',
    staleness_status: index === 0 ? 'aging' : 'fresh',
    provider_url_status: index === 4 ? 'bad' : 'unknown',
    apply_url_status: index === 5 ? 'bad' : 'good',
    repost_count: index === 1 ? 2 : 0,
    dedup_hash: index === 1 ? 'mockdedup123' : '',
    first_seen_at: nowIso(),
    last_seen_at: nowIso(),
    published_at: job.publication_date,
  }))

  return {
    summary: makeDiagnosticsPayload().services.job_board.counts,
    dedup: {
      active_collision_count: 0,
      collision_samples: [],
    },
    recent_syncs: makeMockJobsDebugOverview().recent_syncs,
    recent_inserts: samples.slice(0, 4),
    recent_updates: samples.slice(1, 5),
    bad_provider_urls: samples.filter((row) => row.provider_url_status === 'bad'),
    bad_apply_urls: samples.filter((row) => row.apply_url_status === 'bad'),
    stale_jobs: samples.filter((row) => row.staleness_status !== 'fresh'),
    dedup_owners: samples.filter((row) => row.dedup_hash),
  }
}

function mockGmailConfigured() {
  return true
}

function buildMockConnectedAccounts(state) {
  const googleConnected = Boolean(state.user.google_id)
  const hasPassword = Boolean(state.user.hashed_password)
  return {
    providers: [
      {
        provider: 'google',
        label: 'Google',
        connected: googleConnected,
        account_email: googleConnected ? state.user.email : null,
        can_connect: !googleConnected,
        can_disconnect: googleConnected && hasPassword,
        disconnect_disabled_reason: googleConnected && !hasPassword
          ? 'Set a password before disconnecting your only sign-in method.'
          : null,
        coming_soon: false,
      },
      {
        provider: 'linkedin',
        label: 'LinkedIn',
        connected: false,
        account_email: null,
        can_connect: false,
        can_disconnect: false,
        disconnect_disabled_reason: null,
        coming_soon: true,
      },
    ],
    has_password: hasPassword,
  }
}

function buildMockServiceAction({ key, label, enabled = true, style = 'primary', method = null, href = null }) {
  return { key, label, enabled, style, method, href }
}

function buildMockServiceDetail(state, serviceKey) {
  const normalized = normalizeTextLower(serviceKey)
  const gmailConnected = Boolean(state.user.gmail_refresh_token)
  const gmailConfigured = mockGmailConfigured()

  if (normalized === 'gmail') {
    const connected = gmailConnected
    const status = connected ? 'connected' : (gmailConfigured ? 'available' : 'needs_attention')
    const accountLabel = connected
      ? (state.user.gmail_email || state.user.email)
      : (gmailConfigured ? 'No Gmail mailbox connected yet.' : 'Gmail OAuth is not configured for this environment.')
    return {
      key: 'gmail',
      label: 'Gmail Updates',
      status,
      connected,
      account_label: accountLabel,
      availability: 'available',
      description: 'Connect Gmail so UAH can prepare for inbox-driven job update workflows and future email-based status intelligence.',
      capabilities: [
        'Recognize job-update emails like application receipts, interview invites, and decisions.',
        'Enrich your future application timeline with inbox-derived signals.',
        'Help surface job communication context without making Gmail your sign-in method.',
      ],
      permissions: [
        'Read-only Gmail mailbox access via Google OAuth.',
        'Google account email is used to label the mailbox connection in Settings.',
        'Disconnecting removes the stored refresh token and stops future mailbox access.',
      ],
      readiness: connected
        ? {
            title: 'Ready for mailbox-powered updates',
            description: 'UAH can use this mailbox connection for future job-update scanning, status inference, and timeline enrichment without asking you to reconnect.',
            tone: 'positive',
          }
        : (gmailConfigured
            ? {
                title: 'Available to connect',
                description: 'Connect Gmail when you want UAH ready for inbox-based job update features. Nothing is scanned automatically in this phase.',
                tone: 'neutral',
              }
            : {
                title: 'Needs environment setup',
                description: 'An administrator still needs to configure Gmail OAuth credentials for this environment before users can opt in.',
                tone: 'warning',
              }),
      planned_features: [
        'Inbox-powered application status detection',
        'Timeline enrichment from recruiter communications',
        'Optional service-level scan controls and summaries in a later phase',
      ],
      actions: connected
        ? [buildMockServiceAction({ key: 'disconnect', label: 'Disconnect', style: 'secondary', method: 'DELETE', href: '/api/integrations/gmail/disconnect' })]
        : [gmailConfigured
            ? buildMockServiceAction({ key: 'connect', label: 'Connect', style: 'primary', method: 'POST', href: '/api/integrations/gmail/connect/start' })
            : buildMockServiceAction({ key: 'unavailable', label: 'Unavailable', enabled: false, style: 'muted' })],
    }
  }

  if (normalized === 'calendar_sync') {
    return {
      key: 'calendar_sync',
      label: 'Calendar Sync',
      status: 'coming_soon',
      connected: false,
      account_label: 'Planned for a future release.',
      availability: 'coming_soon',
      description: 'Calendar Sync will help UAH coordinate interview timing, reminders, and event context when the service launches.',
      capabilities: [
        'Match interview invites to tracked applications.',
        'Highlight upcoming conversations and scheduling windows.',
        'Reduce manual copy-and-paste between recruiting emails and your calendar.',
      ],
      permissions: [
        'No calendar access is requested in this release.',
        'Any future calendar permissions will be explained clearly before opt-in.',
      ],
      readiness: {
        title: 'On the roadmap',
        description: 'This service is being designed for a future release and is not yet connectable.',
        tone: 'muted',
      },
      planned_features: [
        'Interview scheduling awareness',
        'Reminder and event enrichment',
        'Meeting context linked back to job applications',
      ],
      actions: [buildMockServiceAction({ key: 'coming_soon', label: 'Coming soon', enabled: false, style: 'muted' })],
    }
  }

  if (normalized === 'resume_imports') {
    return {
      key: 'resume_imports',
      label: 'Resume Imports',
      status: 'coming_soon',
      connected: false,
      account_label: 'Planned for a future release.',
      availability: 'coming_soon',
      description: 'Resume Imports will make it easier to bring documents into UAH from external services without rebuilding your profile by hand.',
      capabilities: [
        'Import resumes and supporting documents from connected storage providers.',
        'Keep document sources organized for future autofill workflows.',
        'Reduce friction when refreshing resumes across multiple applications.',
      ],
      permissions: [
        'No document-provider access is requested in this release.',
        'Future providers will explain exactly which files or folders are shared.',
      ],
      readiness: {
        title: 'Planned for later',
        description: 'This service is intentionally listed early so Settings reads as a reusable integrations hub from day one.',
        tone: 'muted',
      },
      planned_features: [
        'External resume import flows',
        'Document source organization',
        'Future profile/document sync helpers',
      ],
      actions: [buildMockServiceAction({ key: 'coming_soon', label: 'Coming soon', enabled: false, style: 'muted' })],
    }
  }

  return null
}

function listMockServiceSummaries(state) {
  const gmailDetail = buildMockServiceDetail(state, 'gmail')
  const calendarDetail = buildMockServiceDetail(state, 'calendar_sync')
  const resumeImportsDetail = buildMockServiceDetail(state, 'resume_imports')

  return [
    {
      key: gmailDetail.key,
      label: gmailDetail.label,
      category: 'communication',
      status: gmailDetail.status,
      connected: gmailDetail.connected,
      availability: gmailDetail.availability,
      summary: gmailDetail.connected
        ? 'Mailbox ready for future job-update scanning and timeline enrichment.'
        : (mockGmailConfigured()
            ? 'Opt in to read-only inbox access so UAH can prepare for job update workflows.'
            : 'Gmail support exists, but this environment still needs OAuth configuration before users can connect.'),
      account_label: gmailDetail.account_label,
      primary_action: gmailDetail.actions[0],
      can_view_details: true,
    },
    {
      key: calendarDetail.key,
      label: calendarDetail.label,
      category: 'productivity',
      status: calendarDetail.status,
      connected: false,
      availability: calendarDetail.availability,
      summary: 'Prepare for future interview scheduling and reminder enrichment.',
      account_label: calendarDetail.account_label,
      primary_action: calendarDetail.actions[0],
      can_view_details: true,
    },
    {
      key: resumeImportsDetail.key,
      label: resumeImportsDetail.label,
      category: 'documents',
      status: resumeImportsDetail.status,
      connected: false,
      availability: resumeImportsDetail.availability,
      summary: 'Bring resumes and related documents into UAH from future connected sources.',
      account_label: resumeImportsDetail.account_label,
      primary_action: resumeImportsDetail.actions[0],
      can_view_details: true,
    },
  ]
}

function queryValues(params, key) {
  return params.getAll(key).map((value) => normalizeText(value)).filter(Boolean)
}

function cityToMuseLocationName(city) {
  const name = normalizeText(city?.name)
  if (!name) return ''

  const admin = normalizeText(city?.admin1)
  const countryCode = normalizeTextUpper(city?.country_code)
  if (admin && countryCode === 'US') {
    return `${name}, ${admin}`
  }
  if (admin && countryCode && normalizeTextUpper(admin) !== countryCode) {
    return `${name}, ${admin}, ${countryCode}`
  }
  if (countryCode) {
    return `${name}, ${countryCode}`
  }
  return name
}

function buildObservedRankLookup(countryCode) {
  const lookup = new Map()
  const cities = ensureArray(CITY_FIXTURES[countryCode], [])

  for (const [index, city] of cities.entries()) {
    const variants = [
      normalizeTextLower(cityToMuseLocationName(city)),
      normalizeTextLower(city?.name),
      normalizeTextLower(`${normalizeText(city?.name)}, ${normalizeTextUpper(city?.country_code)}`),
    ]

    for (const variant of variants) {
      if (!variant || lookup.has(variant)) continue
      lookup.set(variant, index)
    }
  }

  return lookup
}

function buildMockLocationSelection(params) {
  const mode = normalizeTextLower(params.get('location_mode'))
  const countryCode = normalizeTextUpper(params.get('location_country_code'))
  const rawLocationSelections = queryValues(params, 'location')
  const uniqueLocationSelections = []
  const seenLocations = new Set()

  for (const [index, location] of rawLocationSelections.entries()) {
    const key = normalizeTextLower(location)
    if (!key || seenLocations.has(key)) continue
    seenLocations.add(key)
    uniqueLocationSelections.push({
      value: location,
      key,
      raw_index: index,
    })
  }

  let strategy = 'none'
  let orderedSelections = [...uniqueLocationSelections]

  if (mode === 'country' && orderedSelections.length) {
    strategy = 'muse-index-country-aware'
    const observedRankLookup = buildObservedRankLookup(countryCode)
    orderedSelections.sort((a, b) => {
      const aRank = observedRankLookup.has(a.key) ? observedRankLookup.get(a.key) : Number.MAX_SAFE_INTEGER
      const bRank = observedRankLookup.has(b.key) ? observedRankLookup.get(b.key) : Number.MAX_SAFE_INTEGER
      if (aRank !== bRank) return aRank - bRank
      return a.raw_index - b.raw_index
    })
  } else if ((mode === 'nearby' || mode === 'manual') && orderedSelections.length) {
    strategy = countryCode === 'US'
      ? 'muse-index-country-aware-nearby-state-locked'
      : (countryCode ? 'muse-index-country-aware' : 'muse-index-global')
    orderedSelections.sort((a, b) => a.raw_index - b.raw_index)
  } else if (orderedSelections.length) {
    strategy = countryCode ? 'muse-index-country-aware' : 'muse-index-global'
  }

  const selectedRows = orderedSelections.slice(0, MOCK_LOCATION_PARAM_CAP)
  const droppedRows = orderedSelections.slice(MOCK_LOCATION_PARAM_CAP)
  const selectedLocations = selectedRows.map((row) => row.value)
  const droppedLocations = droppedRows.map((row) => row.value)

  return {
    mode,
    countryCode,
    strategy,
    requestedLocationCount: uniqueLocationSelections.length,
    selectedLocations,
    droppedLocations,
    locationParamsTruncated: droppedLocations.length > 0,
    requestedLocationsSample: uniqueLocationSelections.slice(0, 12).map((row) => row.value),
    selectedLocationsSample: selectedRows.slice(0, 12).map((row) => row.value),
  }
}

function isFlexibleOrRemoteLocationName(name) {
  const normalized = normalizeTextLower(name)
  if (!normalized) return false
  return normalized.includes('remote') || normalized.includes('hybrid') || normalized.includes('flexible')
}

function hasConcreteLocationMatch(jobLocations, selectedLocations) {
  if (!selectedLocations.length) return true
  const lowerLocations = (jobLocations || []).map(normalizeTextLower)

  for (const location of lowerLocations) {
    if (isFlexibleOrRemoteLocationName(location)) continue
    const matched = selectedLocations.some((selected) => location.includes(selected) || selected.includes(location))
    if (matched) return true
  }
  return false
}

function applyJobSearchFilters(baseJobs, params, selectedLocations) {
  let jobs = [...baseJobs]

  const categories = expandCategoriesForMock(queryValues(params, 'category')).map(normalizeTextLower)
  const levels = queryValues(params, 'level').map(normalizeMockLevelValue).filter(Boolean)
  const companies = queryValues(params, 'company').map(normalizeTextLower)
  const provider = normalizeTextLower(params.get('provider'))
  const countryCode = normalizeTextUpper(params.get('location_country_code'))
  const locations = (selectedLocations || []).map(normalizeTextLower)
  const keyword = normalizeTextLower(params.get('q'))
  const postedAfter = parsePostedAfter(params.get('posted_after'))
  const sortBy = normalizeTextLower(params.get('sort_by')) || 'date_desc'

  const includeRemote = normalizeTextLower(params.get('include_remote')) !== 'false'
  const includeHybrid = normalizeTextLower(params.get('include_hybrid')) !== 'false'

  if (provider) {
    jobs = jobs.filter((job) => normalizeTextLower(job.provider) === provider)
  }

  if (countryCode) {
    jobs = jobs.filter((job) => getMockJobCountryCode(job) === countryCode)
  }

  if (categories.length) {
    jobs = jobs.filter((job) => (job.categories || []).some((item) => categories.includes(normalizeTextLower(item))))
  }

  if (levels.length) {
    jobs = jobs.filter((job) => (job.levels || []).some((item) => levels.includes(normalizeMockLevelValue(item))))
  }

  if (companies.length) {
    jobs = jobs.filter((job) => {
      const companyName = normalizeTextLower(job.company)
      return companies.some((company) => companyName.includes(company))
    })
  }

  if (keyword) {
    jobs = jobs.filter((job) => {
      const haystack = [
        job.name,
        job.short_name,
        job.company,
        ...(job.locations || []),
        ...(job.categories || []),
        ...(job.levels || []),
        ...(job.tags || []),
        job.contents || '',
      ].join(' ').toLowerCase()
      return haystack.includes(keyword)
    })
  }

  if (postedAfter) {
    jobs = jobs.filter((job) => matchesPostedAfter(job, postedAfter))
  }

  let acceptedByConcreteLocation = 0
  let acceptedByRemoteOverride = 0
  let acceptedByHybridOverride = 0
  let acceptedByConstraintOverlap = 0

  const allowedJobs = []
  for (const job of jobs) {
    const hasRemote = job.has_remote === true
    const hasHybrid = job.has_hybrid === true
    const remoteOnly = hasRemote && !hasHybrid
    const allowLocalCompatibleRemote = !includeRemote && job.is_local_compatible_remote === true

    const concreteLocationMatch = hasConcreteLocationMatch(job.locations || [], locations)
    let allowReason = locations.length ? 'concrete_location' : 'no-location-filter'

    if (locations.length && !concreteLocationMatch) {
      if (includeRemote && hasRemote) {
        allowReason = 'remote_override'
      } else if (includeHybrid && hasHybrid) {
        allowReason = 'hybrid_override'
      } else if (allowLocalCompatibleRemote && hasRemote) {
        allowReason = 'constraint_overlap'
      } else {
        continue
      }
    }

    if (!includeHybrid && hasHybrid) {
      continue
    }
    if (!includeRemote && remoteOnly && !allowLocalCompatibleRemote) {
      continue
    }

    if (allowReason === 'concrete_location') acceptedByConcreteLocation += 1
    if (allowReason === 'remote_override') acceptedByRemoteOverride += 1
    if (allowReason === 'hybrid_override') acceptedByHybridOverride += 1
    if (allowReason === 'constraint_overlap') acceptedByConstraintOverlap += 1

    allowedJobs.push(job)
  }

  return {
    jobs: sortMockJobs(allowedJobs, sortBy),
    diagnostics: {
      acceptedByConcreteLocation,
      acceptedByRemoteOverride,
      acceptedByHybridOverride,
      acceptedByConstraintOverlap,
      filteredOutCount: Math.max(0, baseJobs.length - allowedJobs.length),
      constraintParseHighConfidence: jobs.length,
      constraintParseMediumConfidence: 0,
      constraintParseLowConfidence: 0,
    },
  }
}

async function parseJsonBody(request) {
  try {
    return await request.clone().json()
  } catch {
    return {}
  }
}

function normalizeProfileContactPayload(body = {}) {
  const next = { ...body }

  if (Object.prototype.hasOwnProperty.call(next, 'email')) {
    const rawEmail = typeof next.email === 'string' ? next.email.trim() : next.email
    next.email = rawEmail ? assertValidEmail(rawEmail) : ''
  }

  if (Object.prototype.hasOwnProperty.call(next, 'phone')) {
    const rawPhone = typeof next.phone === 'string' ? next.phone.trim() : next.phone
    next.phone = rawPhone ? normalizePhone(rawPhone) : ''
  }

  return next
}

async function handleMockApiRequest(request, requestUrl, state) {
  const method = coerceMethod(request.method)
  const pathname = requestUrl.pathname

  if (pathname === '/openapi.json' && method === 'GET') {
    return toJsonResponse({
      openapi: '3.0.0',
      info: {
        title: 'UAH Local Mock API',
        version: '1.0.0',
      },
      paths: {
        '/api/auth/login': {},
        '/api/jobs/filter-metadata': {},
        '/api/jobs/search': {},
        '/api/jobs/debug/overview': {},
        '/api/jobs/debug/db-insights': {},
        '/api/jobs/debug/probe/provider': {},
        '/api/jobs/debug/probe/local-search': {},
        '/api/jobs/debug/probe/live-search': {},
        '/api/providers/attribution': {},
      },
    })
  }

  if (pathname === '/docs' && method === 'GET') {
    return new Response('<html><body><h1>UAH Local Mock Docs</h1><p>Mock mode is active.</p></body></html>', {
      status: 200,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    })
  }

  if ((pathname === '/api' || pathname === '/api/') && method === 'GET') {
    return toJsonResponse({ message: 'UAH local mock API online' })
  }

  if (pathname === '/api/health' && method === 'GET') {
    return toJsonResponse({ status: 'ok', mode: 'mock' })
  }

  if (pathname === '/api/diagnostics' && method === 'GET') {
    return toJsonResponse(makeDiagnosticsPayload())
  }

  if (pathname === '/api/jobs/debug/overview' && method === 'GET') {
    return toJsonResponse(makeMockJobsDebugOverview())
  }

  if (pathname === '/api/jobs/debug/db-insights' && method === 'GET') {
    return toJsonResponse(makeMockJobsDebugInsights())
  }

  if (pathname === '/api/jobs/debug/probe/provider' && method === 'POST') {
    const body = await parseJsonBody(request)
    const provider = normalizeTextLower(body.provider) || 'the_muse'
    return toJsonResponse({
      status: 'ok',
      provider,
      latency_ms: 82,
      request_params: body.params || {},
      item_count: 2,
      sample: JOB_FIXTURES
        .filter((job) => job.provider === provider)
        .slice(0, 2)
        .map((job) => ({
          provider: job.provider,
          provider_job_id: job.provider_job_id,
          provider_url: job.provider_url,
          apply_url: job.apply_url,
          apply_host: '',
          apply_portal: job.apply_portal,
          source_tags: job.source_tags || [],
          title: job.name,
          company: job.company,
          company_url: '',
          location: job.locations?.[0] || '',
          is_remote: job.has_remote === true,
          job_type: job.type,
          experience_level: job.levels?.[0] || '',
          categories: job.categories || [],
          description: job.contents || '',
          published_at: job.publication_date,
        })),
      sample_truncated: 0,
    })
  }

  if (pathname === '/api/jobs/debug/probe/local-search' && method === 'POST') {
    const body = await parseJsonBody(request)
    const payload = buildMockJobsSearchPayload(toSearchParamsFromObject(body.params || {}))
    return toJsonResponse({
      status: 'ok',
      latency_ms: 4,
      request_params: body.params || {},
      payload_hash: 'mocklocal1234',
      response_preview: {
        ...payload,
        jobs: (payload.jobs || []).slice(0, 5),
        jobs_truncated: Math.max((payload.jobs || []).length - 5, 0),
      },
    })
  }

  if (pathname === '/api/jobs/debug/probe/live-search' && method === 'POST') {
    const body = await parseJsonBody(request)
    const payload = buildMockJobsSearchPayload(toSearchParamsFromObject(body.params || {}))
    return toJsonResponse({
      status: 'ok',
      latency_ms: 48,
      request_params: body.params || {},
      payload_hash: 'mocklive12345',
      response_preview: {
        ...payload,
        jobs: (payload.jobs || []).slice(0, 5),
        jobs_truncated: Math.max((payload.jobs || []).length - 5, 0),
      },
    })
  }

  if (pathname === '/api/auth/login' && method === 'POST') {
    const body = await parseJsonBody(request)
    const email = normalizeTextLower(body.email || body.username) || 'localdev@uah.local'

    state.user = {
      ...state.user,
      email,
      username: email,
    }
    const token = makeMockToken(state.user)
    saveState(state)

    return toJsonResponse({
      access_token: token,
      token_type: 'bearer',
      user: state.user,
    })
  }

  if (pathname === '/api/auth/register' && method === 'POST') {
    const body = await parseJsonBody(request)
    const email = normalizeTextLower(body.email) || 'localdev@uah.local'

    state.user = createDefaultUser({
      username: email,
      email,
      first_name: normalizeText(body.first_name) || 'Local',
      last_name: normalizeText(body.last_name) || 'Developer',
    })

    if (!state.profiles.length) {
      state.profiles = [createProfile(state.user)]
    } else {
      state.profiles[0] = {
        ...state.profiles[0],
        first_name: state.user.first_name,
        last_name: state.user.last_name,
        email: state.user.email,
      }
    }

    saveState(state)
    return toJsonResponse({
      access_token: makeMockToken(state.user),
      token_type: 'bearer',
      user: state.user,
    }, 201)
  }

  if (pathname === '/api/auth/logout' && method === 'POST') {
    return toJsonResponse({ message: 'Logged out' })
  }

  if (pathname === '/api/account/forgot-password' && method === 'POST') {
    return toJsonResponse({
      message: 'Reset token generated for local mode',
      token: 'LOCAL-RESET-TOKEN',
    })
  }

  if (pathname === '/api/account/reset-password' && method === 'POST') {
    return toJsonResponse({ message: 'Password reset successfully' })
  }

  if (pathname === '/api/account/verify-email' && method === 'POST') {
    state.user = {
      ...state.user,
      email_verified: true,
    }
    saveState(state)
    return toJsonResponse({ message: 'Email verified' })
  }

  const auth = requireAuth(pathname, state)
  if (!auth.ok) return auth.response

  if (pathname === '/api/auth/me' && method === 'GET') {
    return toJsonResponse(state.user)
  }

  if (pathname === '/api/auth/connected-accounts' && method === 'GET') {
    return toJsonResponse(buildMockConnectedAccounts(state))
  }

  if (pathname === '/api/auth/google/connect/start' && method === 'POST') {
    state.user = {
      ...state.user,
      google_id: state.user.google_id || 'mock-google-account',
    }
    saveState(state)
    return toJsonResponse({
      authorization_url: `${window.location.origin}/settings?accounts=connected&provider=google`,
    })
  }

  if (pathname === '/api/auth/google/disconnect' && method === 'DELETE') {
    if (!state.user.google_id) {
      return toJsonResponse({ message: 'Google account already disconnected' })
    }

    if (!state.user.hashed_password) {
      return toJsonResponse(
        { detail: 'Cannot disconnect Google without another sign-in method. Set a password first.' },
        400
      )
    }

    state.user = {
      ...state.user,
      google_id: null,
    }
    saveState(state)
    return toJsonResponse({ message: 'Google account disconnected' })
  }

  if (pathname === '/api/integrations/services' && method === 'GET') {
    return toJsonResponse(listMockServiceSummaries(state))
  }

  const integrationServiceMatch = pathname.match(/^\/api\/integrations\/services\/([^/]+)$/)
  if (integrationServiceMatch && method === 'GET') {
    const detail = buildMockServiceDetail(state, integrationServiceMatch[1])
    if (!detail) {
      return toJsonResponse({ detail: 'Service not found' }, 404)
    }
    return toJsonResponse(detail)
  }

  if (pathname === '/api/integrations/gmail/status' && method === 'GET') {
    return toJsonResponse({
      connected: Boolean(state.user.gmail_refresh_token),
      email: state.user.gmail_email,
    })
  }

  if (pathname === '/api/integrations/gmail/connect/start' && method === 'POST') {
    if (!mockGmailConfigured()) {
      return toJsonResponse({ detail: 'not_configured' }, 400)
    }

    state.user = {
      ...state.user,
      gmail_refresh_token: 'mock-gmail-refresh-token',
      gmail_email: state.user.email,
    }
    saveState(state)
    return toJsonResponse({
      authorization_url: `${window.location.origin}/settings?service=gmail&service_state=connected`,
    })
  }

  if (pathname === '/api/integrations/gmail/disconnect' && method === 'DELETE') {
    state.user = {
      ...state.user,
      gmail_refresh_token: null,
      gmail_email: null,
    }
    saveState(state)
    return toJsonResponse({ message: 'Gmail disconnected' })
  }

  if (pathname === '/api/account/change-name' && method === 'PUT') {
    const body = await parseJsonBody(request)
    state.user = {
      ...state.user,
      first_name: normalizeText(body.first_name) || state.user.first_name,
      last_name: normalizeText(body.last_name) || state.user.last_name,
    }

    const activeProfile = state.profiles.find((profile) => profile.is_active) || state.profiles[0]
    if (activeProfile) {
      activeProfile.first_name = state.user.first_name
      activeProfile.last_name = state.user.last_name
    }

    saveState(state)
    return toJsonResponse(state.user)
  }

  if (pathname === '/api/account/change-password' && method === 'PUT') {
    return toJsonResponse({ message: 'Password changed successfully' })
  }

  if (pathname === '/api/account/change-email' && method === 'PUT') {
    const body = await parseJsonBody(request)
    let nextEmail = ''

    try {
      nextEmail = assertValidEmail(body.new_email, 'new email')
    } catch (error) {
      return toJsonResponse({ detail: error?.message || 'Please enter a valid email address' }, 400)
    }

    if (!nextEmail) {
      return toJsonResponse({ detail: 'new_email is required' }, 400)
    }

    state.user = {
      ...state.user,
      email: nextEmail,
      username: nextEmail,
      email_verified: false,
    }

    const activeProfile = state.profiles.find((profile) => profile.is_active) || state.profiles[0]
    if (activeProfile) {
      activeProfile.email = nextEmail
    }

    saveState(state)
    return toJsonResponse({ message: 'Email updated' })
  }

  if (pathname === '/api/account/change-username' && method === 'PUT') {
    return toJsonResponse(
      { detail: 'Username updates are deprecated. Email is now the sign-in identifier.' },
      410
    )
  }

  if (pathname === '/api/account/send-verification' && method === 'POST') {
    return toJsonResponse({
      message: 'Verification token generated in local mode',
      token: 'LOCAL-VERIFY-TOKEN',
    })
  }

  if (pathname === '/api/account/delete' && method === 'DELETE') {
    return toJsonResponse({ message: 'Account deleted in local mode' })
  }

  if ((pathname === '/api/resume/' || pathname === '/api/resume') && method === 'GET') {
    state.resumes = state.resumes.map((resume) => syncMockResumeRecord(resume))
    saveState(state)
    return toJsonResponse(asJson(state.resumes))
  }

  if (pathname === '/api/resume/upload' && method === 'POST') {
    let fileName = 'uploaded_resume.pdf'
    try {
      const form = await request.formData()
      const file = form.get('file')
      if (file && typeof file === 'object' && 'name' in file) {
        fileName = normalizeText(file.name) || fileName
      }
    } catch {
      // Keep fallback filename when form parsing is unavailable.
    }

    const id = state.nextIds.resume
    state.nextIds.resume += 1

    const uploaded = createResume(id, state.user, {
      file_name: fileName,
      parse_method: null,
      portal_ready: false,
      structured_data: null,
      review_status: '',
      review_draft: null,
      review_updated_at: null,
    })

    state.resumes.unshift(uploaded)
    saveState(state)

    return toJsonResponse(asJson(uploaded), 201)
  }

  const resumeParseMatch = pathname.match(/^\/api\/resume\/(\d+)\/parse-async$/)
  if (resumeParseMatch && method === 'POST') {
    const body = await parseJsonBody(request)
    const resumeId = Number(resumeParseMatch[1])
    const methodName = normalizeTextLower(body.method) || 'local'

    const resumeExists = state.resumes.some((resume) => Number(resume.id) === resumeId)
    if (!resumeExists) {
      return toJsonResponse({ detail: 'Resume not found' }, 404)
    }

    const jobId = String(state.nextIds.parseJob)
    state.nextIds.parseJob += 1

    state.parseJobs[jobId] = {
      job_id: jobId,
      resume_id: resumeId,
      method: methodName,
      status: 'queued',
      progress_stage: 'Queued',
      created_at: nowIso(),
      updated_at: nowIso(),
      poll_count: 0,
      attempt: 1,
      elapsed_seconds: 0,
      error_code: null,
      error_message: null,
    }

    saveState(state)
    return toJsonResponse({ job_id: jobId, status: 'queued' }, 202)
  }

  const parseJobMatch = pathname.match(/^\/api\/resume\/parse-job\/([^/]+)$/)
  if (parseJobMatch && method === 'GET') {
    const jobId = parseJobMatch[1]
    const job = state.parseJobs[jobId]
    if (!job) {
      return toJsonResponse({ detail: 'Parse job not found' }, 404)
    }

    advanceParseJobState(state, job)
    const elapsed = Math.max(1, Math.round((Date.now() - Date.parse(job.created_at)) / 1000))
    job.elapsed_seconds = elapsed

    const activeJobs = Object.values(state.parseJobs).filter((item) => ['queued', 'parsing', 'validating'].includes(item.status))
    const queuePosition = activeJobs.findIndex((item) => item.job_id === job.job_id) + 1

    const payload = {
      job_id: job.job_id,
      resume_id: job.resume_id,
      status: job.status,
      progress_stage: job.progress_stage,
      attempt: job.attempt,
      elapsed_seconds: elapsed,
      queue_position: queuePosition > 0 ? queuePosition : null,
      queue_total: activeJobs.length || null,
      error_code: job.error_code,
      error_message: job.error_message,
      result_summary: job.result_summary || null,
      queue_snapshot: buildQueueSnapshot(state, job.method, false),
    }

    saveState(state)
    return toJsonResponse(payload)
  }

  const parseCancelMatch = pathname.match(/^\/api\/resume\/parse-job\/([^/]+)\/cancel$/)
  if (parseCancelMatch && method === 'POST') {
    const jobId = parseCancelMatch[1]
    const job = state.parseJobs[jobId]
    if (!job) {
      return toJsonResponse({ detail: 'Parse job not found' }, 404)
    }

    job.status = 'cancelled'
    job.progress_stage = 'Cancelled'
    job.updated_at = nowIso()
    saveState(state)

    return toJsonResponse({ message: 'Parse cancelled' })
  }

  if (pathname === '/api/resume/queue/status' && method === 'GET') {
    const scope = normalizeTextLower(requestUrl.searchParams.get('scope')) || 'user'
    const focusMethod = normalizeTextLower(requestUrl.searchParams.get('focus_method')) || 'local'
    const includeGlobal = scope === 'global'

    return toJsonResponse(buildQueueSnapshot(state, focusMethod, includeGlobal))
  }

  const resumePdfMatch = pathname.match(/^\/api\/resume\/(\d+)\/pdf$/)
  if (resumePdfMatch && method === 'GET') {
    const resumeId = Number(resumePdfMatch[1])
    const resume = state.resumes.find((item) => Number(item.id) === resumeId)

    if (!resume) {
      return toJsonResponse({ detail: 'Resume not found' }, 404)
    }

    return toPdfResponse()
  }

  const resumeByIdMatch = pathname.match(/^\/api\/resume\/(\d+)$/)
  if (resumeByIdMatch && method === 'GET') {
    const resumeId = Number(resumeByIdMatch[1])
    const resume = state.resumes.find((item) => Number(item.id) === resumeId)

    if (!resume) {
      return toJsonResponse({ detail: 'Resume not found' }, 404)
    }

    return toJsonResponse(asJson(syncMockResumeRecord(resume)))
  }

  const reviewDraftMatch = pathname.match(/^\/api\/resume\/(\d+)\/review-draft$/)
  if (reviewDraftMatch && method === 'GET') {
    const resumeId = Number(reviewDraftMatch[1])
    const resume = state.resumes.find((item) => Number(item.id) === resumeId)
    if (!resume) {
      return toJsonResponse({ detail: 'Resume not found' }, 404)
    }
    const reviewDraft = resume.review_draft || resume.structured_data
    if (!reviewDraft) {
      return toJsonResponse({ detail: 'Resume has not been parsed yet' }, 400)
    }
    return toJsonResponse({
      resume_id: resume.id,
      file_name: resume.file_name,
      parse_method: resume.parse_method,
      review_status: resume.review_status || 'pending',
      review_updated_at: resume.review_updated_at,
      review_draft: reviewDraft,
    })
  }

  if (reviewDraftMatch && method === 'PUT') {
    const resumeId = Number(reviewDraftMatch[1])
    const resumeIndex = state.resumes.findIndex((item) => Number(item.id) === resumeId)
    if (resumeIndex < 0) {
      return toJsonResponse({ detail: 'Resume not found' }, 404)
    }
    const body = await parseJsonBody(request)
    state.resumes[resumeIndex] = syncMockResumeRecord({
      ...state.resumes[resumeIndex],
      review_status: 'pending',
      review_draft: body.review_draft || state.resumes[resumeIndex].review_draft || state.resumes[resumeIndex].structured_data,
      review_updated_at: nowIso(),
    })
    saveState(state)
    return toJsonResponse({
      resume_id: state.resumes[resumeIndex].id,
      file_name: state.resumes[resumeIndex].file_name,
      parse_method: state.resumes[resumeIndex].parse_method,
      review_status: state.resumes[resumeIndex].review_status,
      review_updated_at: state.resumes[resumeIndex].review_updated_at,
      review_draft: state.resumes[resumeIndex].review_draft,
    })
  }

  const reviewConflictsMatch = pathname.match(/^\/api\/resume\/(\d+)\/review-conflicts$/)
  if (reviewConflictsMatch && method === 'POST') {
    const resumeId = Number(reviewConflictsMatch[1])
    const resume = state.resumes.find((item) => Number(item.id) === resumeId)
    if (!resume) {
      return toJsonResponse({ detail: 'Resume not found' }, 404)
    }
    const body = await parseJsonBody(request)
    const profile = state.profiles.find((item) => Number(item.id) === Number(body.profile_id))
    if (!profile) {
      return toJsonResponse({ detail: 'Profile not found' }, 404)
    }
    const incoming = normalizeCanonicalData(body.reviewed_data || resume.review_draft || resume.structured_data)
    const existing = normalizeCanonicalData(profile.canonical_data || {})
    const conflicts = generateMockReviewConflicts(existing, incoming)
    return toJsonResponse({ profile_id: profile.id, conflict_count: conflicts.length, conflicts })
  }

  const applyReviewMatch = pathname.match(/^\/api\/resume\/(\d+)\/apply-review$/)
  if (applyReviewMatch && method === 'POST') {
    const resumeId = Number(applyReviewMatch[1])
    const resumeIndex = state.resumes.findIndex((item) => Number(item.id) === resumeId)
    if (resumeIndex < 0) {
      return toJsonResponse({ detail: 'Resume not found' }, 404)
    }
    const body = await parseJsonBody(request)
    const incoming = normalizeCanonicalData(body.reviewed_data)
    let profile = null
    let conflicts = []

    if (body.mode === 'existing') {
      const profileIndex = state.profiles.findIndex((item) => Number(item.id) === Number(body.profile_id))
      if (profileIndex < 0) {
        return toJsonResponse({ detail: 'Profile not found' }, 404)
      }
      const merge = mergeMockReviewIntoProfile(state.profiles[profileIndex].canonical_data || {}, incoming, body.conflict_resolutions || {})
      conflicts = merge.conflicts
      profile = syncMockProfileStorage({
        ...state.profiles[profileIndex],
        canonical_data: merge.merged,
        is_active: true,
        updated_at: nowIso(),
      })
      state.profiles = state.profiles.map((item, index) => index === profileIndex ? profile : { ...item, is_active: false })
    } else if (body.mode === 'new') {
      const id = state.nextIds.profile
      state.nextIds.profile += 1
      state.profiles = state.profiles.map((item) => ({ ...item, is_active: false }))
      profile = syncMockProfileStorage(createProfile(state.user, id, {
        name: cleanProfileString(body.profile_name) || cleanProfileString(incoming.personal_info.first_name) || `Profile ${id}`,
        is_default: false,
        is_active: true,
        canonical_data: incoming,
        updated_at: nowIso(),
      }))
      state.profiles.push(profile)
    } else {
      return toJsonResponse({ detail: "Mode must be 'existing' or 'new'" }, 400)
    }

    if (profile?.is_active) {
      state.user = {
        ...state.user,
        first_name: profile.first_name || state.user.first_name,
        last_name: profile.last_name || state.user.last_name,
        email: profile.email || state.user.email,
      }
    }

    state.resumes[resumeIndex] = syncMockResumeRecord({
      ...state.resumes[resumeIndex],
      review_status: 'applied',
      review_draft: body.reviewed_data,
      review_updated_at: nowIso(),
      updated_at: nowIso(),
    })
    saveState(state)
    return toJsonResponse({
      resume_id: state.resumes[resumeIndex].id,
      profile_id: profile.id,
      review_status: state.resumes[resumeIndex].review_status,
      conflict_count: conflicts.length,
      profile: asJson(profile),
    })
  }

  if (resumeByIdMatch && method === 'DELETE') {
    const resumeId = Number(resumeByIdMatch[1])
    state.resumes = state.resumes.filter((item) => Number(item.id) !== resumeId)
    saveState(state)
    return toJsonResponse({ message: 'Resume deleted' })
  }

  if ((pathname === '/api/applicant-profile/' || pathname === '/api/applicant-profile') && method === 'GET') {
    state.profiles = state.profiles.map((profile) => syncMockProfileStorage(profile))
    saveState(state)
    return toJsonResponse(asJson(state.profiles))
  }

  if ((pathname === '/api/applicant-profile/' || pathname === '/api/applicant-profile') && method === 'POST') {
    let body = await parseJsonBody(request)
    try {
      body = normalizeProfileContactPayload(body)
    } catch (error) {
      return toJsonResponse({ detail: error?.message || 'Please enter valid contact details' }, 400)
    }
    const id = state.nextIds.profile
    state.nextIds.profile += 1

    const created = createProfile(state.user, id, {
      ...body,
      name: normalizeText(body.name) || `Profile ${id}`,
      is_default: state.profiles.length === 0 || body.is_default === true,
      is_active: body.is_default === true || state.profiles.length === 0,
      created_at: nowIso(),
    })

    if (created.is_active) {
      state.profiles = state.profiles.map((profile) => ({ ...profile, is_active: false }))
    }

    state.profiles.push(syncMockProfileStorage(created))
    saveState(state)
    return toJsonResponse(asJson(state.profiles[state.profiles.length - 1]), 201)
  }

  const profileByIdMatch = pathname.match(/^\/api\/applicant-profile\/(\d+)$/)
  if (profileByIdMatch && method === 'GET') {
    const profileId = Number(profileByIdMatch[1])
    const profile = state.profiles.find((item) => Number(item.id) === profileId)

    if (!profile) {
      return toJsonResponse({ detail: 'Profile not found' }, 404)
    }

    const synced = syncMockProfileStorage(profile)
    state.profiles = state.profiles.map((item) => Number(item.id) === profileId ? synced : item)
    saveState(state)
    return toJsonResponse(asJson(synced))
  }

  if (profileByIdMatch && method === 'PUT') {
    const profileId = Number(profileByIdMatch[1])
    const profileIndex = state.profiles.findIndex((item) => Number(item.id) === profileId)

    if (profileIndex < 0) {
      return toJsonResponse({ detail: 'Profile not found' }, 404)
    }

    let body = await parseJsonBody(request)
    try {
      body = normalizeProfileContactPayload(body)
    } catch (error) {
      return toJsonResponse({ detail: error?.message || 'Please enter valid contact details' }, 400)
    }
    state.profiles[profileIndex] = syncMockProfileStorage({
      ...state.profiles[profileIndex],
      ...body,
      id: profileId,
      updated_at: nowIso(),
    })

    if (state.profiles[profileIndex].is_active) {
      state.user = {
        ...state.user,
        first_name: state.profiles[profileIndex].first_name || state.user.first_name,
        last_name: state.profiles[profileIndex].last_name || state.user.last_name,
        email: state.profiles[profileIndex].email || state.user.email,
      }
    }

    saveState(state)
    return toJsonResponse(asJson(state.profiles[profileIndex]))
  }

  if (profileByIdMatch && method === 'DELETE') {
    const profileId = Number(profileByIdMatch[1])
    const profile = state.profiles.find((item) => Number(item.id) === profileId)

    if (!profile) {
      return toJsonResponse({ detail: 'Profile not found' }, 404)
    }

    if (profile.is_default) {
      return toJsonResponse({ detail: 'Default profile cannot be deleted' }, 400)
    }

    state.profiles = state.profiles.filter((item) => Number(item.id) !== profileId)

    if (!state.profiles.some((item) => item.is_active) && state.profiles.length) {
      state.profiles[0].is_active = true
    }

    saveState(state)
    return toJsonResponse({ message: 'Profile deleted' })
  }

  const profileActivateMatch = pathname.match(/^\/api\/applicant-profile\/(\d+)\/activate$/)
  if (profileActivateMatch && method === 'POST') {
    const profileId = Number(profileActivateMatch[1])
    let activeProfile = null

    state.profiles = state.profiles.map((profile) => {
      const isActive = Number(profile.id) === profileId
      const next = { ...profile, is_active: isActive }
      if (isActive) activeProfile = next
      return next
    })

    if (!activeProfile) {
      return toJsonResponse({ detail: 'Profile not found' }, 404)
    }

    state.user = {
      ...state.user,
      first_name: activeProfile.first_name || state.user.first_name,
      last_name: activeProfile.last_name || state.user.last_name,
      email: activeProfile.email || state.user.email,
    }

    activeProfile = syncMockProfileStorage(activeProfile)
    state.profiles = state.profiles.map((profile) => Number(profile.id) === profileId ? activeProfile : profile)
    saveState(state)
    return toJsonResponse(asJson(activeProfile))
  }

  if (pathname === '/api/geolocation/muse-supported-countries' && method === 'GET') {
    return toJsonResponse({ countries: COUNTRY_FIXTURES, total_count: COUNTRY_FIXTURES.length })
  }

  if (pathname === '/api/jobs/filter-metadata' && method === 'GET') {
    return toJsonResponse(buildMockFilterMetadata())
  }

  if (pathname === '/api/providers/attribution' && method === 'GET') {
    return toJsonResponse({
      providers: Object.values(PROVIDER_ATTRIBUTION_FIXTURES).map((provider) => asJson(provider)),
    })
  }

  if (pathname === '/api/geolocation/ip' && method === 'GET') {
    return toJsonResponse({
      city: 'Huntsville',
      state: 'AL',
      country: 'United States',
      country_code: 'US',
      latitude: 34.7304,
      longitude: -86.5861,
      source: 'mock-ip',
      accuracy_km: 25,
      display_name: 'Huntsville, AL, US',
    })
  }

  if (pathname === '/api/geolocation/reverse' && method === 'GET') {
    const latitude = Number(requestUrl.searchParams.get('latitude') || '0')
    const longitude = Number(requestUrl.searchParams.get('longitude') || '0')
    const nearest = allCities()
      .map((city) => ({ city, distance: haversineMiles(latitude, longitude, city.latitude, city.longitude) }))
      .sort((a, b) => a.distance - b.distance)[0]

    if (!nearest) {
      return toJsonResponse({ detail: 'No location candidates found' }, 404)
    }

    return toJsonResponse({
      ...nearest.city,
      display_name: `${nearest.city.name}, ${nearest.city.admin1}, ${nearest.city.country_code}`,
      source: 'mock-reverse',
    })
  }

  if (pathname === '/api/geolocation/geocode' && method === 'GET') {
    const query = normalizeTextLower(requestUrl.searchParams.get('q'))
    const countryCode = normalizeTextUpper(requestUrl.searchParams.get('country_code'))

    const candidates = allCities().filter((city) => {
      if (countryCode && city.country_code !== countryCode) return false
      if (!query) return true

      const haystack = `${city.name} ${city.admin1} ${city.country} ${city.country_code}`.toLowerCase()
      return haystack.includes(query)
    })

    const match = candidates[0] || null
    if (!match) {
      return toJsonResponse({ detail: 'No geocode match found' }, 404)
    }

    return toJsonResponse({
      ...match,
      display_name: `${match.name}, ${match.admin1}, ${match.country_code}`,
      source: 'mock-geocode',
    })
  }

  if (pathname === '/api/geolocation/muse-supported-locations' && method === 'GET') {
    const countryCode = normalizeTextUpper(requestUrl.searchParams.get('country_code')) || 'US'
    const limit = Math.max(1, Math.min(500, parseInteger(requestUrl.searchParams.get('limit'), 200)))
    const locations = ensureArray(CITY_FIXTURES[countryCode], [])
      .map((city, index) => ({
        name: cityToMuseLocationName(city),
        admin1: city.admin1,
        country: city.country,
        country_code: city.country_code,
        latitude: city.latitude,
        longitude: city.longitude,
        observed_count: Math.max(1, 1000 - index * 50),
      }))
      .sort((a, b) => Number(b.observed_count || 0) - Number(a.observed_count || 0))
      .slice(0, limit)
    return toJsonResponse({ locations, total_count: locations.length, country_code: countryCode })
  }

  if (pathname === '/api/geolocation/country-cities' && method === 'GET') {
    const countryCode = normalizeTextUpper(requestUrl.searchParams.get('country_code')) || 'US'
    const cities = ensureArray(CITY_FIXTURES[countryCode], []).map((city) => ({ ...city }))
    return toJsonResponse({ cities })
  }

  if (pathname === '/api/geolocation/cities-in-radius' && method === 'GET') {
    const latitude = Number(requestUrl.searchParams.get('latitude') || '0')
    const longitude = Number(requestUrl.searchParams.get('longitude') || '0')
    const radius = Number(requestUrl.searchParams.get('radius') || '25')
    const unit = normalizeTextLower(requestUrl.searchParams.get('unit')) || 'mi'
    const countryCode = normalizeTextUpper(requestUrl.searchParams.get('country_code'))

    const radiusMiles = unit === 'km' ? radius * 0.621371 : radius
    const cities = allCities().filter((city) => {
      if (countryCode && city.country_code !== countryCode) return false
      const distanceMiles = haversineMiles(latitude, longitude, city.latitude, city.longitude)
      return distanceMiles <= Math.max(radiusMiles, 1)
    })

    return toJsonResponse({
      cities: cities.length ? cities : allCities().slice(0, 4),
    })
  }

  if (pathname === '/api/jobs/search' && method === 'GET') {
    return toJsonResponse(buildMockJobsSearchPayload(requestUrl.searchParams))
  }

  return toJsonResponse({ detail: `No mock handler for ${method} ${pathname}` }, 404)
}

function normalizeTextUpper(value) {
  return normalizeText(value).toUpperCase()
}

function shouldInterceptApi(requestUrl) {
  const pathname = requestUrl.pathname || ''
  return pathname.startsWith('/api/') || pathname === '/api' || pathname === '/docs' || pathname === '/openapi.json'
}

function shouldBlockRemoteApiInMockMode(requestUrl) {
  if (!shouldInterceptApi(requestUrl)) return false

  const hostname = requestUrl.hostname
  if (!hostname) return false

  return !isLoopbackHost(hostname) && requestUrl.origin !== window.location.origin
}

export function initializeLocalMockApi() {
  if (typeof window === 'undefined') return false
  if (mockFetchInstalled) return true
  if (getFrontendLocalMode() !== 'mock') return false

  const state = loadState()
  maybeBootstrapAutoLogin(state)
  saveState(state)

  const nativeFetch = window.fetch.bind(window)

  window.fetch = async (input, init = {}) => {
    const request = new Request(input, init)
    const requestUrl = new URL(request.url, window.location.origin)

    if (!shouldInterceptApi(requestUrl)) {
      return nativeFetch(input, init)
    }

    if (shouldBlockRemoteApiInMockMode(requestUrl)) {
      return toJsonResponse({ detail: 'Remote API calls are blocked in local mock mode.' }, 403)
    }

    try {
      const currentState = ensureStateShape(loadState())
      const response = await handleMockApiRequest(request, requestUrl, currentState)
      saveState(currentState)
      return response
    } catch (error) {
      console.error('local mock api error', error)
      return toJsonResponse({ detail: 'Local mock API error', error: String(error?.message || error) }, 500)
    }
  }

  mockFetchInstalled = true
  return true
}
