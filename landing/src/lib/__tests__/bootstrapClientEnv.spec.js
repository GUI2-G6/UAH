import { describe, expect, it } from 'vitest'

import { markJsEnabled } from '../bootstrapClientEnv.js'

describe('bootstrap client environment', () => {
  it('marks the document root as js-enabled for mobile-nav CSS gates', () => {
    document.documentElement.classList.remove('js-enabled')

    markJsEnabled()

    expect(document.documentElement.classList.contains('js-enabled')).toBe(true)
  })
})
