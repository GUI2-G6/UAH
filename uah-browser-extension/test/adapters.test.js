import test from 'node:test'
import assert from 'node:assert/strict'

import BaseATSAdapter from '../src/adapters/base/BaseATSAdapter.js'
import WorkdayAdapter from '../src/adapters/ats/WorkdayAdapter.js'
import GreenhouseAdapter from '../src/adapters/ats/GreenhouseAdapter.js'
import LeverAdapter from '../src/adapters/ats/LeverAdapter.js'
import ICIMSAdapter from '../src/adapters/ats/iCIMSAdapter.js'
import TaleoAdapter from '../src/adapters/ats/TaleoAdapter.js'
import ExampleCorpWorkdayAdapter from '../src/adapters/companies/workday/ExampleCorpWorkdayAdapter.js'
import ExampleCorpGreenhouseAdapter from '../src/adapters/companies/greenhouse/ExampleCorpGreenhouseAdapter.js'

function createFakeElement({
  tagName = 'INPUT',
  type = 'text',
  id = '',
  name = '',
  label = '',
  required = false,
  ariaLabel = '',
}) {
  return {
    tagName,
    type,
    id,
    required,
    disabled: false,
    offsetParent: {},
    parentElement: null,
    closest() {
      return null
    },
    getBoundingClientRect() {
      return { width: 120, height: 32 }
    },
    getAttribute(attribute) {
      switch (attribute) {
        case 'name':
          return name || null
        case 'aria-label':
          return ariaLabel || null
        case 'aria-required':
          return required ? 'true' : null
        case 'placeholder':
        case 'data-label':
        default:
          return null
      }
    },
    __label: label,
  }
}

function createFakeDocument(elements = []) {
  const labelMap = new Map(
    elements
      .filter((element) => element.id && element.__label)
      .map((element) => [element.id, { textContent: element.__label }])
  )

  return {
    querySelectorAll(selector) {
      if (selector === 'input, textarea, select') {
        return elements
      }

      return []
    },
    querySelector(selector) {
      const labelMatch = selector.match(/^label\[for="(.+)"\]$/)
      if (labelMatch) {
        return labelMap.get(labelMatch[1]) || null
      }

      return null
    },
  }
}

async function loadRegistryModule(seed) {
  return import(`../src/adapters/index.js?seed=${seed}`)
}

test('BaseATSAdapter throws for abstract methods and returns default base metadata', () => {
  const adapter = new BaseATSAdapter({
    document: createFakeDocument(),
    location: 'https://example.com/apply',
  })

  assert.throws(() => adapter.matches('https://example.com'), /must implement matches/)
  assert.throws(() => adapter.getATSName(), /must implement getATSName/)
  assert.equal(adapter.getCompanyName(), null)
  assert.equal(adapter.getSupportLevel(), 'base')
  assert.equal(adapter.isApplicationPage(), true)
})

test('BaseATSAdapter.detectFormFields returns the documented map shape', () => {
  const document = createFakeDocument([
    createFakeElement({
      name: 'first_name',
      id: 'first_name',
      label: 'First name',
      required: true,
    }),
    createFakeElement({
      id: 'job_location',
      label: 'Job location',
      tagName: 'SELECT',
      type: 'select-one',
    }),
    createFakeElement({
      ariaLabel: 'Work Authorization',
    }),
  ])

  const adapter = new BaseATSAdapter({ document, location: 'https://example.com/jobs/apply' })
  const fields = adapter.detectFormFields()

  assert.deepEqual(fields.first_name, {
    label: 'First name',
    type: 'text',
    required: true,
    tagName: 'input',
    name: 'first_name',
    id: 'first_name',
  })
  assert.deepEqual(fields.job_location, {
    label: 'Job location',
    type: 'select-one',
    required: false,
    tagName: 'select',
    name: '',
    id: 'job_location',
  })
  assert.deepEqual(fields['work-authorization'], {
    label: 'Work Authorization',
    type: 'text',
    required: false,
    tagName: 'input',
    name: '',
    id: '',
  })
})

test('WorkdayAdapter matches the supported Workday URL patterns', () => {
  const adapter = new WorkdayAdapter()

  assert.equal(adapter.matches('https://examplecorp.wd1.myworkdayjobs.com/en-US/careers/job/123'), true)
  assert.equal(adapter.matches('https://contoso.wd3.myworkdayjobs.com/en-US/jobs'), true)
  assert.equal(adapter.matches('https://fabrikam.wd5.myworkdayjobs.com/en-US/apply'), true)
  assert.equal(adapter.matches('https://northwind.myworkdayjobs.com/en-US/careers'), true)
  assert.equal(adapter.matches('https://boards.greenhouse.io/examplecorp'), false)
})

test('GreenhouseAdapter matches the supported Greenhouse URL patterns', () => {
  const adapter = new GreenhouseAdapter()

  assert.equal(adapter.matches('https://boards.greenhouse.io/examplecorp/jobs/12345'), true)
  assert.equal(adapter.matches('https://examplecorp.greenhouse.io/jobs/12345'), true)
  assert.equal(adapter.matches('https://jobs.lever.co/examplecorp/abc123'), false)
})

test('LeverAdapter matches the supported Lever URL patterns', () => {
  const adapter = new LeverAdapter()

  assert.equal(adapter.matches('https://jobs.lever.co/examplecorp/abc123'), true)
  assert.equal(adapter.matches('https://examplecorp.jobs.lever.co/abc123'), false)
})

test('ICIMSAdapter matches the supported iCIMS URL patterns', () => {
  const adapter = new ICIMSAdapter()

  assert.equal(adapter.matches('https://careers.examplecorp.icims.com/jobs/1234/job'), true)
  assert.equal(adapter.matches('https://examplecorp.icims.com/jobs/1234/job'), true)
  assert.equal(adapter.matches('https://jobs.examplecorp.icims.com/jobs/1234/job'), false)
})

test('TaleoAdapter matches Taleo career section URL patterns', () => {
  const adapter = new TaleoAdapter()
  assert.equal(adapter.matches('https://xyz.taleo.net/careersection/2/jobdetail.ftl?job=123'), true)
  assert.equal(adapter.matches('https://company.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1'), true)
  assert.equal(adapter.matches('https://boards.greenhouse.io/examplecorp/jobs/12345'), false)
})

test('ExampleCorpWorkdayAdapter merges company-specific fields on top of the base adapter', () => {
  const document = createFakeDocument([
    createFakeElement({
      name: 'first_name',
      id: 'first_name',
      label: 'First name',
    }),
    createFakeElement({
      ariaLabel: 'Work Authorization',
    }),
  ])

  const adapter = new ExampleCorpWorkdayAdapter({
    document,
    location: 'https://examplecorp.wd1.myworkdayjobs.com/en-US/apply',
  })

  const fields = adapter.detectFormFields()
  assert.equal(fields.first_name.label, 'First name')
  assert.deepEqual(fields.workAuthorization, {
    label: 'Work Authorization',
    type: 'text',
    required: false,
    tagName: 'input',
    name: '',
    id: '',
  })
  assert.equal(adapter.getSupportLevel(), 'partial')
})

test('ExampleCorpGreenhouseAdapter reports partial support and recognizes its hosted board', () => {
  const adapter = new ExampleCorpGreenhouseAdapter({
    document: createFakeDocument(),
    location: 'https://boards.greenhouse.io/examplecorp/jobs/12345',
  })

  assert.equal(adapter.matches('https://boards.greenhouse.io/examplecorp/jobs/12345'), true)
  assert.equal(adapter.matches('https://boards.greenhouse.io/not-examplecorp/jobs/12345'), false)
  assert.equal(adapter.getSupportLevel(), 'partial')
})

test('registry resolves company overrides before base ATS adapters', async () => {
  const registry = await loadRegistryModule('resolve-priority')
  const adapter = registry.resolveAdapter('https://examplecorp.wd1.myworkdayjobs.com/en-US/careers/job/123')

  assert.equal(adapter?.constructor?.name, 'ExampleCorpWorkdayAdapter')
  assert.equal(adapter?.getATSName(), 'Workday')
  assert.equal(adapter?.getCompanyName(), 'Example Corp')
})

test('registry returns supported ATS names and company override metadata', async () => {
  const registry = await loadRegistryModule('metadata')

  assert.deepEqual(registry.getSupportedATS(), ['Workday', 'Greenhouse', 'Lever', 'iCIMS', 'Taleo'])
  assert.deepEqual(registry.getCompanyOverrides(), [
    {
      atsName: 'Workday',
      companyName: 'Example Corp',
      adapterName: 'ExampleCorpWorkdayAdapter',
    },
    {
      atsName: 'Greenhouse',
      companyName: 'Example Corp',
      adapterName: 'ExampleCorpGreenhouseAdapter',
    },
  ])
})

test('registry returns null for unsupported URLs and validates dynamic registrations', async () => {
  const registry = await loadRegistryModule('dynamic-registration')

  assert.equal(registry.resolveAdapter('https://example.com/jobs/123'), null)
  assert.throws(() => registry.registerAdapter({}), /missing matches/)

  class CustomATSAdapter extends BaseATSAdapter {
    matches(url) {
      return String(url).includes('custom-ats.example.com')
    }

    getATSName() {
      return 'CustomATS'
    }
  }

  registry.registerAdapter(new CustomATSAdapter())

  assert.deepEqual(
    registry.getSupportedATS(),
    ['Workday', 'Greenhouse', 'Lever', 'iCIMS', 'Taleo', 'CustomATS'],
  )
  assert.equal(
    registry.resolveAdapter('https://custom-ats.example.com/jobs/apply')?.getATSName(),
    'CustomATS',
  )
})
