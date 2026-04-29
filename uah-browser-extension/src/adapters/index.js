import WorkdayAdapter from './ats/WorkdayAdapter.js'
import GreenhouseAdapter from './ats/GreenhouseAdapter.js'
import LeverAdapter from './ats/LeverAdapter.js'
import ICIMSAdapter from './ats/iCIMSAdapter.js'
import TaleoAdapter from './ats/TaleoAdapter.js'
import DynamicsAdapter from './ats/DynamicsAdapter.js'
import ExampleCorpWorkdayAdapter from './companies/workday/ExampleCorpWorkdayAdapter.js'
import ExampleCorpGreenhouseAdapter from './companies/greenhouse/ExampleCorpGreenhouseAdapter.js'

const REQUIRED_METHODS = [
  'matches',
  'getATSName',
  'getCompanyName',
  'detectJobDetails',
  'detectFormFields',
  'isApplicationPage',
  'getSupportLevel',
]

const baseAdapters = []
const companyOverrides = []

function validateAdapter(adapter) {
  if (!adapter || typeof adapter !== 'object') {
    throw new TypeError('Adapter must be an object instance.')
  }

  for (const methodName of REQUIRED_METHODS) {
    if (typeof adapter[methodName] !== 'function') {
      throw new TypeError(`Adapter ${adapter.constructor?.name || '(anonymous)'} is missing ${methodName}().`)
    }
  }
}

function normalizeUrl(url) {
  const rawUrl = String(url || '').trim()
  if (!rawUrl) return ''

  try {
    return new URL(rawUrl).toString()
  } catch {
    return rawUrl
  }
}

export function registerAdapter(adapter) {
  validateAdapter(adapter)

  const companyName = String(adapter.getCompanyName() || '').trim()
  if (companyName) {
    companyOverrides.push(adapter)
    return
  }

  baseAdapters.push(adapter)
}

export function resolveAdapter(url) {
  const normalizedUrl = normalizeUrl(url)
  if (!normalizedUrl) return null

  // Company overrides are more specific than the generic ATS matchers and must
  // win first when one employer deviates from the platform defaults.
  for (const adapter of companyOverrides) {
    if (adapter.matches(normalizedUrl)) {
      return adapter
    }
  }

  for (const adapter of baseAdapters) {
    if (adapter.matches(normalizedUrl)) {
      return adapter
    }
  }

  return null
}

export function getSupportedATS() {
  const names = []
  const seen = new Set()

  // Report supported platform families, not every company-specific override.
  for (const adapter of baseAdapters) {
    const atsName = adapter.getATSName()
    if (seen.has(atsName)) continue
    seen.add(atsName)
    names.push(atsName)
  }

  return names
}

export function getCompanyOverrides() {
  return companyOverrides.map((adapter) => ({
    atsName: adapter.getATSName(),
    companyName: adapter.getCompanyName(),
    adapterName: adapter.constructor.name,
  }))
}

registerAdapter(new WorkdayAdapter())
registerAdapter(new GreenhouseAdapter())
registerAdapter(new LeverAdapter())
registerAdapter(new ICIMSAdapter())
registerAdapter(new TaleoAdapter())
registerAdapter(new DynamicsAdapter())
registerAdapter(new ExampleCorpWorkdayAdapter())
registerAdapter(new ExampleCorpGreenhouseAdapter())
