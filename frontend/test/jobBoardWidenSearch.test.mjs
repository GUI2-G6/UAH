import test from 'node:test'
import assert from 'node:assert/strict'

import { getWidenSearchPlan } from '../src/lib/jobBoardWidenSearch.js'

test('widen search increases manual miles radius in fixed steps', () => {
  const plan = getWidenSearchPlan({
    locationMode: 'manual',
    locationRadius: 25,
    radiusUnit: 'mi',
    countryCode: 'US',
    includeRemote: false,
    includeHybrid: false,
  }, {
    allCountriesCode: 'ALL',
    countryName: 'United States',
  })

  assert.equal(plan.canWiden, true)
  assert.equal(plan.action, 'increase-radius')
  assert.equal(plan.label, 'Widen to 50 mi')
  assert.equal(plan.nextFilters.locationRadius, 50)
  assert.equal(plan.nextFilters.includeRemote, false)
  assert.equal(plan.nextFilters.includeHybrid, false)
})

test('widen search switches max nearby radius to country mode', () => {
  const plan = getWidenSearchPlan({
    locationMode: 'nearby',
    locationRadius: 100,
    radiusUnit: 'mi',
    countryCode: 'US',
    locationNames: ['Huntsville, AL'],
  }, {
    allCountriesCode: 'ALL',
    countryName: 'United States',
  })

  assert.equal(plan.canWiden, true)
  assert.equal(plan.action, 'switch-country')
  assert.equal(plan.label, 'Switch to United States')
  assert.equal(plan.nextFilters.locationMode, 'country')
  assert.deepEqual(plan.nextFilters.locationNames, [])
})

test('widen search escalates country scope to all countries', () => {
  const plan = getWidenSearchPlan({
    locationMode: 'country',
    countryCode: 'DE',
  }, {
    allCountriesCode: 'ALL',
    countryName: 'Germany',
  })

  assert.equal(plan.canWiden, true)
  assert.equal(plan.action, 'switch-all-countries')
  assert.equal(plan.label, 'Search all countries')
  assert.equal(plan.nextFilters.countryCode, 'ALL')
})

test('widen search disables itself once all countries is already active', () => {
  const plan = getWidenSearchPlan({
    locationMode: 'country',
    countryCode: 'ALL',
  }, {
    allCountriesCode: 'ALL',
  })

  assert.equal(plan.canWiden, false)
  assert.equal(plan.action, 'none')
  assert.equal(plan.nextFilters, null)
})

