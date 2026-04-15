import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPlan, resolveNameToPath } from '../src/autofill/matching.js'
import { fillField, fillPlan, isFieldRequired } from '../src/autofill/dom.js'
import { buildProfileAutofillSource, sanitizeTokenMap } from '../src/autofill/source.js'
import { flattenResume } from '../src/autofill/shared.js'
import {
  buildDefaultFloatingPosition,
  clampPanelSize,
  clampFloatingPosition,
  mergePinnedUiState,
  normalizeFloatingPosition,
} from '../src/lib/pinnedUiState.js'

function createDispatchingElement(overrides = {}) {
  const events = []
  const element = {
    tagName: 'INPUT',
    type: 'text',
    value: '',
    focus() {},
    dispatchEvent(event) {
      events.push(event.type)
      return true
    },
    ...overrides,
  }
  return { element, events }
}

test('buildProfileAutofillSource prefers token_map and overlays profile-only extras', () => {
  const source = buildProfileAutofillSource({
    id: 12,
    name: 'Default Profile',
    token_map: {
      'personal_info.first_name': 'Taylor',
      'education[0].institution': 'UAH',
    },
    work_auth: 'Authorized to work in the US',
    requires_sponsorship: 'No',
    years_experience: '5',
    professional_links_text: 'GitHub: https://github.com/example',
  })

  assert.equal(source.source.type, 'profile')
  assert.equal(source.source.profileId, 12)
  assert.equal(source.source.profileName, 'Default Profile')
  assert.equal(source.tokenMap['personal_info.first_name'], 'Taylor')
  assert.equal(source.tokenMap.work_auth, 'Authorized to work in the US')
  assert.equal(source.tokenMap.requires_sponsorship, 'No')
  assert.equal(source.tokenMap.years_experience, '5')
  assert.equal(source.tokenMap.professional_links_text, 'GitHub: https://github.com/example')
})

test('sanitizeTokenMap keeps only structured-clone-safe flat primitives', () => {
  const tokenMap = sanitizeTokenMap({
    'personal_info.first_name': 'Taylor',
    'skills.technical': ['JavaScript', 'Vue'],
    years_experience: 5,
    requires_sponsorship: false,
    nested: { nope: true },
    fn: () => 'bad',
    blank: '   ',
  })

  assert.deepEqual(tokenMap, {
    'personal_info.first_name': 'Taylor',
    'skills.technical': 'JavaScript, Vue',
    years_experience: 5,
    requires_sponsorship: false,
  })
})

test('flattenResume keeps legacy date splitting behavior for present and expected dates', () => {
  const tokens = flattenResume({
    personal_info: { first_name: 'Taylor', last_name: 'Example' },
    education: [
      {
        institution: 'UAH',
        degree: 'B.S.',
        field_of_study: 'Computer Science',
        start_date: 'August 2022',
        end_date: 'Expected May 2026',
      },
    ],
    work_experience: [
      {
        company: 'OpenAI',
        title: 'Engineer',
        start_date: 'June 2024',
        end_date: 'Present',
        bullets: ['Built tools', 'Shipped features'],
      },
    ],
  })

  assert.equal(tokens['education[0].start_month'], 'August')
  assert.equal(tokens['education[0].start_year'], '2022')
  assert.equal(tokens['education[0].end_month'], 'May')
  assert.equal(tokens['education[0].end_year'], '2026')
  assert.equal(tokens['work_experience[0].start_month'], 'June')
  assert.equal(tokens['work_experience[0].start_year'], '2024')
  assert.equal(tokens['work_experience[0].is_current'], true)
  assert.equal(tokens['work_experience[0].bullets'], 'Built tools\nShipped features')
})

test('resolveNameToPath supports direct, indexed, and checkbox aliases', () => {
  assert.equal(resolveNameToPath('first_name'), 'personal_info.first_name')
  assert.equal(resolveNameToPath('education[0].school'), 'education[0].institution')
  assert.equal(resolveNameToPath('currently_work_here_2'), 'work_experience[2].is_current')
  assert.equal(resolveNameToPath('work-authorization'), 'work_auth')
})

test('buildPlan preserves name, id, synonym, review, and no-match behavior', () => {
  const tokenMap = {
    'personal_info.first_name': 'Taylor',
    'personal_info.email': 'taylor@example.com',
    work_auth: 'Authorized to work in the US',
    'skills.technical': 'JavaScript, Vue',
  }

  const plan = buildPlan([
    { name: 'first_name', id: '', labelNorm: 'ignored', required: false, el: {} },
    { name: '', id: 'email', labelNorm: 'ignored', required: false, el: {} },
    { name: '', id: '', labelNorm: 'authorized to work', required: false, el: {} },
    { name: '', id: '', labelNorm: 'technical skills summary', required: false, el: {} },
    { name: '', id: '', labelNorm: 'favorite color', required: true, el: {} },
  ], tokenMap)

  assert.equal(plan[0].matchPath, 'personal_info.first_name')
  assert.equal(plan[0].matchScore, 1)
  assert.equal(plan[1].matchPath, 'personal_info.email')
  assert.equal(plan[1].matchScore, 0.95)
  assert.equal(plan[2].matchPath, 'work_auth')
  assert.ok(plan[2].matchScore >= 0.75)
  assert.equal(plan[3].matchPath, 'skills.technical')
  assert.equal(plan[3].matchScore, 0.55)
  assert.equal(plan[4].matchPath, null)
  assert.equal(plan[4].matchScore, 0)
})

test('isFieldRequired checks required, aria-required, and star labels', () => {
  assert.equal(isFieldRequired({ required: true }), true)
  assert.equal(isFieldRequired({ ariaRequired: true }), true)
  assert.equal(isFieldRequired({ label: 'Phone *' }), true)
  assert.equal(isFieldRequired({ label: 'Phone' }), false)
})

test('fillField handles text, select, checkbox, and radio fields', () => {
  const textField = createDispatchingElement()
  assert.equal(fillField(textField.element, 'Taylor'), true)
  assert.equal(textField.element.value, 'Taylor')
  assert.deepEqual(textField.events, ['input', 'change', 'blur'])

  const selectField = createDispatchingElement({
    tagName: 'SELECT',
    type: 'select-one',
    value: '',
    options: [
      { textContent: 'Alabama', value: 'AL' },
      { textContent: 'Georgia', value: 'GA' },
    ],
  })
  assert.equal(fillField(selectField.element, 'Alabama'), true)
  assert.equal(selectField.element.value, 'AL')

  let checkboxClicked = 0
  const checkboxField = {
    tagName: 'INPUT',
    type: 'checkbox',
    checked: false,
    click() {
      checkboxClicked += 1
      this.checked = true
    },
  }
  assert.equal(fillField(checkboxField, true), true)
  assert.equal(checkboxClicked, 1)

  let radioClicked = 0
  const radioField = {
    tagName: 'INPUT',
    type: 'radio',
    value: 'No',
    click() {
      radioClicked += 1
    },
  }
  assert.equal(fillField(radioField, 'no'), true)
  assert.equal(radioClicked, 1)
})

test('fillPlan fills current checkboxes first and skips end date tokens when current', () => {
  const order = []
  const currentField = {
    tagName: 'INPUT',
    type: 'checkbox',
    checked: false,
    click() {
      order.push('current')
      this.checked = true
    },
  }
  const endDateField = createDispatchingElement({
    tagName: 'INPUT',
    type: 'text',
    focus() {
      order.push('end-date')
    },
  })

  const filled = fillPlan([
    { el: endDateField.element, matchPath: 'work_experience[0].end_year', matchScore: 0.9 },
    { el: currentField, matchPath: 'work_experience[0].is_current', matchScore: 0.9 },
  ], {
    'work_experience[0].is_current': true,
    'work_experience[0].end_year': '2026',
  })

  assert.equal(filled, 1)
  assert.deepEqual(order, ['current'])
  assert.equal(endDateField.element.value, '')
})

test('mergePinnedUiState normalizes persisted pin state and positions', () => {
  const state = mergePinnedUiState(undefined, {
    pinEnabled: true,
    panelPosition: { top: '24', left: 18.2 },
    panelSize: { width: '480', height: 620.4 },
    panelResizeUnlocked: true,
    debugPosition: null,
  })

  assert.equal(state.pinEnabled, true)
  assert.deepEqual(state.panelPosition, { top: 24, left: 18 })
  assert.deepEqual(state.panelSize, { width: 480, height: 620 })
  assert.equal(state.panelResizeUnlocked, true)
  assert.equal(state.debugPosition, null)
})

test('locked panel size helper returns the default pinned footprint', async () => {
  const { buildLockedPanelSize } = await import('../src/lib/pinnedUiState.js')
  assert.deepEqual(
    buildLockedPanelSize({ viewportWidth: 1600, viewportHeight: 1000 }),
    { width: 196, height: 380 },
  )
})

test('floating position helpers clamp persisted coordinates into the viewport', () => {
  assert.deepEqual(normalizeFloatingPosition({ top: 10.7, left: '42' }), { top: 11, left: 42 })
  assert.deepEqual(
    buildDefaultFloatingPosition({ viewportWidth: 900, width: 300, top: 20 }),
    { top: 20, left: 584 },
  )
  assert.deepEqual(
    clampFloatingPosition(
      { top: -10, left: 9999 },
      { viewportWidth: 800, viewportHeight: 600, width: 300, height: 200 },
    ),
    { top: 16, left: 484 },
  )
  assert.deepEqual(
    clampPanelSize(
      { width: 9999, height: 100 },
      { viewportWidth: 800, viewportHeight: 600 },
    ),
    { width: 720, height: 320 },
  )
})
