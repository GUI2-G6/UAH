import test from 'node:test'
import assert from 'node:assert/strict'

import { formatJobLocationDisplay } from '../src/lib/jobLocationDisplay.js'

test('location display strips duplicate country names before adding the flag', () => {
  const display = formatJobLocationDisplay({
    location: 'Berlin, Germany',
    location_country_code: 'DE',
    location_country_name: 'Germany',
  })

  assert.equal(display.label, 'Berlin 🇩🇪')
  assert.equal(display.title, 'Berlin · Germany')
  assert.equal(display.rawLocation, 'Berlin')
})

test('location display strips duplicate country codes from raw locations', () => {
  const display = formatJobLocationDisplay({
    location: 'Boston, MA, US',
    location_country_code: 'US',
    location_country_name: 'United States',
  })

  assert.equal(display.label, 'Boston, MA 🇺🇸')
  assert.equal(display.title, 'Boston, MA · United States')
})

test('location display keeps sentinel countries flag-free', () => {
  const display = formatJobLocationDisplay({
    location: '',
    location_country_code: 'XX',
    location_country_name: 'Remote / Global',
  })

  assert.equal(display.label, 'Remote / Global')
  assert.equal(display.flag, '')
})

