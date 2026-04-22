import { readFileSync } from 'node:fs'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import BetaAccess from '../BetaAccess.vue'
import PartnersSection from '../PartnersSection.vue'
import SiteFooter from '../SiteFooter.vue'
import SiteHeader from '../SiteHeader.vue'
import WishlistForm from '../WishlistForm.vue'

describe('public landing mail routing', () => {
  it('routes beta, partnership, feedback, and footer contact actions to the right inboxes', () => {
    const beta = mount(BetaAccess)
    const partners = mount(PartnersSection)
    const wishlist = mount(WishlistForm)
    const footer = mount(SiteFooter)
    const footerMailtoLinks = footer.findAll('.footer-links a[href^="mailto:"]').map((link) => link.attributes('href'))

    expect(beta.get('.access-links .button').attributes('href')).toBe(
      'mailto:beta@uahapp.com?subject=UAH Beta Access Request'
    )
    expect(partners.get('.partner-cta .button').attributes('href')).toBe(
      'mailto:partners@uahapp.com?subject=UAH Partnership Inquiry'
    )
    expect(wishlist.get('form').attributes('action')).toBe('mailto:feedback@uahapp.com')
    expect(footerMailtoLinks).toContain('mailto:team@uahapp.com')
    expect(footerMailtoLinks).toContain('mailto:press@uahapp.com')
  })
})

describe('public landing search verification metadata', () => {
  it('keeps the Google site verification tag in the landing document head', () => {
    const indexHtml = readFileSync('index.html', 'utf8')

    expect(indexHtml).toContain('google-site-verification')
    expect(indexHtml).toContain('qbLaNwcx_OeOrBgJ5Bn6U_CeS_C7ganwGjeimDhRRHw')
  })
})

describe('public landing mobile navigation', () => {
  afterEach(() => {
    document.body.className = ''
  })

  it('keeps the drawer open while the viewport is still within the mobile breakpoint', async () => {
    window.innerWidth = 800

    const wrapper = mount(SiteHeader)
    await wrapper.get('.nav-toggle').trigger('click')
    await nextTick()

    expect(wrapper.get('.nav-toggle').attributes('aria-expanded')).toBe('true')
    expect(document.body.classList.contains('nav-open')).toBe(true)

    window.innerWidth = 900
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect(wrapper.get('.nav-toggle').attributes('aria-expanded')).toBe('true')
    expect(document.body.classList.contains('nav-open')).toBe(true)
  })
})
