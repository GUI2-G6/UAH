const MOCK_STATE_KEY = 'uah_mock_state_v1'
const ACCESS_TOKEN_KEY = 'uah_access_token'
const CURRENT_USER_KEY = 'uah_current_user'

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

const JOB_FIXTURES = [
  {
    id: 'mock-job-1001',
    name: 'Frontend Engineer (Vue)',
    short_name: 'Frontend Engineer',
    company: 'Atlas Systems',
    locations: ['Huntsville, AL'],
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
    publication_date: '2026-04-05T09:00:00Z',
    job_url: 'https://example.com/jobs/mock-job-1001',
    contents: 'Build and ship frontend features with Vue and modern tooling.',
  },
  {
    id: 'mock-job-1002',
    name: 'Backend Python Engineer',
    short_name: 'Backend Engineer',
    company: 'Data Forge',
    locations: ['Austin, TX'],
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
    publication_date: '2026-04-02T11:30:00Z',
    job_url: 'https://example.com/jobs/mock-job-1002',
    contents: 'Own API performance and queue reliability.',
  },
  {
    id: 'mock-job-1003',
    name: 'Product Designer',
    short_name: 'Product Designer',
    company: 'Northwind Studio',
    locations: ['Boston, MA'],
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
    publication_date: '2026-04-06T13:45:00Z',
    job_url: 'https://example.com/jobs/mock-job-1003',
    contents: 'Design recruiting workflows and dashboard UX.',
  },
  {
    id: 'mock-job-1004',
    name: 'Data Analyst',
    short_name: 'Data Analyst',
    company: 'Peak Metrics',
    locations: ['Seattle, WA'],
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
    publication_date: '2026-03-31T15:15:00Z',
    job_url: 'https://example.com/jobs/mock-job-1004',
    contents: 'Create analytics for hiring funnel performance.',
  },
  {
    id: 'mock-job-1005',
    name: 'Security Engineer',
    short_name: 'Security Engineer',
    company: 'ShieldOps',
    locations: ['Chicago, IL'],
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
    publication_date: '2026-04-01T08:20:00Z',
    job_url: 'https://example.com/jobs/mock-job-1005',
    contents: 'Develop secure defaults and incident tooling.',
  },
  {
    id: 'mock-job-1006',
    name: 'QA Automation Engineer',
    short_name: 'QA Automation',
    company: 'Blue Pine Labs',
    locations: ['Toronto, ON'],
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
    publication_date: '2026-04-07T10:05:00Z',
    job_url: 'https://example.com/jobs/mock-job-1006',
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
    username: user.username,
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
  const explicit = import.meta.env.VITE_LOCAL_MODE
  if (explicit) return normalizeMode(explicit)

  if (import.meta.env.MODE === 'backend') return 'backend'
  if (import.meta.env.MODE === 'mock') return 'mock'
  return 'mock'
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
  return {
    id: 1,
    username: 'localdev',
    email: 'localdev@uah.local',
    email_verified: true,
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
  return {
    id,
    file_name: `Resume_${id}.pdf`,
    created_at: createdAt,
    parse_method: 'local',
    portal_ready: true,
    has_pdf: true,
    structured_data: createResumeStructuredData(user),
    ...overrides,
  }
}

function createProfile(user, id = 1, overrides = {}) {
  const createdAt = nowIso()
  return {
    id,
    name: 'Default',
    is_active: true,
    is_default: true,
    created_at: createdAt,
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
  }
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
  safe.user = safe.user && typeof safe.user === 'object' ? safe.user : createDefaultUser()
  safe.resumes = ensureArray(safe.resumes, [])
  safe.profiles = ensureArray(safe.profiles, [])
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
  const token = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (!token) return null

  try {
    const raw = localStorage.getItem(CURRENT_USER_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    return state.user || null
  }

  return state.user || null
}

function setAuthStorage(user) {
  const token = makeMockToken(user)
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user))
}

function maybeBootstrapAutoLogin(state) {
  const autoLogin = parseBoolean(import.meta.env.VITE_LOCAL_AUTO_LOGIN, false)
  if (!autoLogin) return

  if (!localStorage.getItem(ACCESS_TOKEN_KEY)) {
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

  state.resumes[resumeIndex] = updated
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
    },
  }
}

function queryValues(params, key) {
  return params.getAll(key).map((value) => normalizeText(value)).filter(Boolean)
}

function applyJobSearchFilters(baseJobs, params) {
  let jobs = [...baseJobs]

  const categories = queryValues(params, 'category').map(normalizeTextLower)
  const levels = queryValues(params, 'level').map(normalizeTextLower)
  const companies = queryValues(params, 'company').map(normalizeTextLower)
  const locations = queryValues(params, 'location').map(normalizeTextLower)

  const includeRemote = normalizeTextLower(params.get('include_remote')) === 'true'
  const includeHybrid = normalizeTextLower(params.get('include_hybrid')) !== 'false'

  if (categories.length) {
    jobs = jobs.filter((job) => (job.categories || []).some((item) => categories.includes(normalizeTextLower(item))))
  }

  if (levels.length) {
    jobs = jobs.filter((job) => (job.levels || []).some((item) => levels.includes(normalizeTextLower(item))))
  }

  if (companies.length) {
    jobs = jobs.filter((job) => companies.includes(normalizeTextLower(job.company)))
  }

  if (locations.length) {
    jobs = jobs.filter((job) => {
      const lowerLocations = (job.locations || []).map(normalizeTextLower)
      return locations.some((selected) => lowerLocations.some((candidate) => candidate.includes(selected)))
    })
  }

  jobs = jobs.filter((job) => {
    if (!includeHybrid && job.has_hybrid) return false

    const remoteOnly = job.has_remote === true && job.has_hybrid !== true
    if (!includeRemote && remoteOnly && job.is_local_compatible_remote !== true) return false

    return true
  })

  return jobs
}

async function parseJsonBody(request) {
  try {
    return await request.clone().json()
  } catch {
    return {}
  }
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
        '/api/jobs/search': {},
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

  if (pathname === '/api/auth/login' && method === 'POST') {
    const body = await parseJsonBody(request)
    const username = normalizeText(body.username) || 'localdev'

    state.user = {
      ...state.user,
      username,
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

    state.user = createDefaultUser({
      username: normalizeText(body.username) || 'localdev',
      email: normalizeText(body.email) || 'localdev@uah.local',
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
    const nextEmail = normalizeText(body.new_email)

    if (!nextEmail) {
      return toJsonResponse({ detail: 'new_email is required' }, 400)
    }

    state.user = {
      ...state.user,
      email: nextEmail,
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
    const body = await parseJsonBody(request)
    const nextUsername = normalizeText(body.new_username)

    if (!nextUsername) {
      return toJsonResponse({ detail: 'new_username is required' }, 400)
    }

    state.user = {
      ...state.user,
      username: nextUsername,
    }
    saveState(state)

    return toJsonResponse(state.user)
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
    })

    state.resumes.unshift(uploaded)
    saveState(state)

    return toJsonResponse(uploaded, 201)
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

    return toJsonResponse(asJson(resume))
  }

  if (resumeByIdMatch && method === 'DELETE') {
    const resumeId = Number(resumeByIdMatch[1])
    state.resumes = state.resumes.filter((item) => Number(item.id) !== resumeId)
    saveState(state)
    return toJsonResponse({ message: 'Resume deleted' })
  }

  if ((pathname === '/api/applicant-profile/' || pathname === '/api/applicant-profile') && method === 'GET') {
    return toJsonResponse(asJson(state.profiles))
  }

  if ((pathname === '/api/applicant-profile/' || pathname === '/api/applicant-profile') && method === 'POST') {
    const body = await parseJsonBody(request)
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

    state.profiles.push(created)
    saveState(state)
    return toJsonResponse(created, 201)
  }

  const profileByIdMatch = pathname.match(/^\/api\/applicant-profile\/(\d+)$/)
  if (profileByIdMatch && method === 'GET') {
    const profileId = Number(profileByIdMatch[1])
    const profile = state.profiles.find((item) => Number(item.id) === profileId)

    if (!profile) {
      return toJsonResponse({ detail: 'Profile not found' }, 404)
    }

    return toJsonResponse(asJson(profile))
  }

  if (profileByIdMatch && method === 'PUT') {
    const profileId = Number(profileByIdMatch[1])
    const profileIndex = state.profiles.findIndex((item) => Number(item.id) === profileId)

    if (profileIndex < 0) {
      return toJsonResponse({ detail: 'Profile not found' }, 404)
    }

    const body = await parseJsonBody(request)
    state.profiles[profileIndex] = {
      ...state.profiles[profileIndex],
      ...body,
      id: profileId,
    }

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

    saveState(state)
    return toJsonResponse(asJson(activeProfile))
  }

  if (pathname === '/api/geolocation/muse-supported-countries' && method === 'GET') {
    return toJsonResponse({ countries: COUNTRY_FIXTURES })
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
    const locations = ensureArray(CITY_FIXTURES[countryCode], []).map((city) => ({ ...city }))
    return toJsonResponse({ locations })
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
    const page = Math.max(1, parseInteger(requestUrl.searchParams.get('page'), 1))
    const pageSize = Math.max(1, Math.min(50, parseInteger(requestUrl.searchParams.get('page_size'), 10)))

    const filtered = applyJobSearchFilters(JOB_FIXTURES, requestUrl.searchParams)
    const totalJobs = filtered.length
    const totalPages = Math.max(1, Math.ceil(totalJobs / pageSize))
    const start = (page - 1) * pageSize
    const jobs = filtered.slice(start, start + pageSize)

    const locationSelections = queryValues(requestUrl.searchParams, 'location')

    return toJsonResponse({
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
      filtered_out_count: Math.max(0, JOB_FIXTURES.length - totalJobs),
      requested_location_count: locationSelections.length,
      used_location_count: locationSelections.length,
      location_params_used: locationSelections.length,
      location_params_truncated: false,
      has_next_page_possible_raw: page < totalPages,
      has_more_source_pages: page < totalPages,
      source_page_count: totalPages,
      window_start_page: page,
      window_size: 1,
      location_selection_strategy: 'mock',
      canonicalized_location_count: locationSelections.length,
      transformed_location_count: locationSelections.length,
      unmatched_location_count: 0,
      strict_state_blocked_count: 0,
      selected_state_diversity_count: 1,
      accepted_by_concrete_location: totalJobs,
      accepted_by_remote_override: 0,
      accepted_by_hybrid_override: 0,
      accepted_by_constraint_overlap: 0,
      constraint_parse_high_confidence: totalJobs,
      constraint_parse_medium_confidence: 0,
      constraint_parse_low_confidence: 0,
      constraint_compatibility_enabled: true,
      constraint_filter_min_confidence: 'high',
      adaptive_chase_enabled: false,
      adaptive_chase_extra_pages: 0,
      effective_max_pages: 1,
      effective_min_filtered_ratio: 0,
      requested_locations_sample: locationSelections.slice(0, 5),
      selected_locations_sample: locationSelections.slice(0, 5),
      cache_hit: false,
    })
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
