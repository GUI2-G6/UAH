const DEFAULT_WIDEN_STEP_BY_UNIT = Object.freeze({
  mi: 25,
  km: 40,
})

const DEFAULT_MAX_RADIUS_BY_UNIT = Object.freeze({
  mi: 100,
  km: 161,
})

function normalizeCountryCode(value) {
  return String(value || '').trim().toUpperCase()
}

function normalizeLocationMode(value) {
  const normalized = String(value || '').trim().toLowerCase()
  return ['country', 'nearby', 'manual'].includes(normalized) ? normalized : 'country'
}

function normalizeRadiusUnit(value) {
  return String(value || '').trim().toLowerCase() === 'km' ? 'km' : 'mi'
}

function isAllCountriesCode(value, allCountriesCode = 'ALL') {
  return normalizeCountryCode(value) === normalizeCountryCode(allCountriesCode || 'ALL')
}

function clampRadius(value, maximum) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return 25
  return Math.max(1, Math.min(maximum, Math.round(numeric)))
}

export function getWidenSearchPlan(filters = {}, options = {}) {
  const allCountriesCode = normalizeCountryCode(options.allCountriesCode || 'ALL') || 'ALL'
  const countryCode = normalizeCountryCode(filters.countryCode) || allCountriesCode
  const countryName = String(options.countryName || '').trim()
  const locationMode = normalizeLocationMode(filters.locationMode)
  const radiusUnit = normalizeRadiusUnit(filters.radiusUnit)
  const maxRadiusByUnit = options.maxRadiusByUnit || DEFAULT_MAX_RADIUS_BY_UNIT
  const stepByUnit = options.stepByUnit || DEFAULT_WIDEN_STEP_BY_UNIT
  const maxRadius = Number(maxRadiusByUnit?.[radiusUnit]) || DEFAULT_MAX_RADIUS_BY_UNIT[radiusUnit]
  const nextStep = Number(stepByUnit?.[radiusUnit]) || DEFAULT_WIDEN_STEP_BY_UNIT[radiusUnit]

  if (locationMode === 'manual' || locationMode === 'nearby') {
    const currentRadius = clampRadius(filters.locationRadius, maxRadius)
    if (currentRadius < maxRadius) {
      const nextRadius = Math.min(maxRadius, currentRadius + nextStep)
      return {
        canWiden: true,
        action: 'increase-radius',
        label: `Widen to ${nextRadius} ${radiusUnit}`,
        nextFilters: {
          ...filters,
          locationRadius: nextRadius,
          radiusUnit,
        },
      }
    }

    return {
      canWiden: true,
      action: isAllCountriesCode(countryCode, allCountriesCode) ? 'switch-all-countries' : 'switch-country',
      label: isAllCountriesCode(countryCode, allCountriesCode)
        ? 'Search all countries'
        : `Switch to ${countryName || countryCode}`,
      nextFilters: {
        ...filters,
        locationMode: 'country',
        countryCode,
        locationNames: [],
      },
    }
  }

  if (locationMode === 'country' && !isAllCountriesCode(countryCode, allCountriesCode)) {
    return {
      canWiden: true,
      action: 'switch-all-countries',
      label: 'Search all countries',
      nextFilters: {
        ...filters,
        countryCode: allCountriesCode,
        locationNames: [],
      },
    }
  }

  return {
    canWiden: false,
    action: 'none',
    label: 'Widen search',
    nextFilters: null,
  }
}

