import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import BrowserExtensionPage from '../../pages/BrowserExtensionPage.vue'

describe('browser extension page docs links', () => {
  it('uses stable site-hosted docs links for install and security guides', () => {
    const wrapper = mount(BrowserExtensionPage)
    const anchors = wrapper.findAll('a')
    const hrefs = anchors.map((anchor) => anchor.attributes('href'))

    expect(hrefs).toContain('/docs/BROWSER_EXTENSION_CHROME_INSTALL.md')
    expect(hrefs).toContain('/docs/BROWSER_EXTENSION_EASY_INSTALL.md')
    expect(hrefs).toContain('/docs/UAH_BROWSER_EXTENSION_SECURITY.md')
  })
})
