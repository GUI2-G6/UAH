import { readFileSync } from 'node:fs'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import BetaAccess from '../BetaAccess.vue'
import PartnersSection from '../PartnersSection.vue'
import SiteFooter from '../SiteFooter.vue'
import SiteHeader from '../SiteHeader.vue'
import WishlistForm from '../WishlistForm.vue'
import PublicStatusPage from '../../pages/PublicStatusPage.vue'
import landingRouter from '../../router/index.js'

const routerLinkStub = {
  props: ['to'],
  template: '<a :href="typeof to === \'string\' ? to : String(to)"><slot /></a>',
}

function mountHeader() {
  return mount(SiteHeader, {
    global: {
      stubs: {
        RouterLink: routerLinkStub,
      },
    },
  })
}

describe('public landing mail routing', () => {
  it('routes beta, partnership, feedback, and footer contact actions to the right inboxes', () => {
    const beta = mount(BetaAccess)
    const partners = mount(PartnersSection)
    const wishlist = mount(WishlistForm)
    const footer = mount(SiteFooter, {
      global: {
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a :href="typeof to === \'string\' ? to : String(to)"><slot /></a>',
          },
        },
      },
    })
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

    const wrapper = mountHeader()
    await wrapper.get('.nav-toggle').trigger('click')
    await nextTick()

    expect(wrapper.get('.nav-toggle').attributes('aria-expanded')).toBe('true')
    expect(document.body.classList.contains('nav-open')).toBe(true)

    window.innerWidth = 900
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect(wrapper.get('.nav-toggle').attributes('aria-expanded')).toBe('true')
    expect(document.body.classList.contains('nav-open')).toBe(true)

    window.innerWidth = 1280
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect(wrapper.get('.nav-toggle').attributes('aria-expanded')).toBe('false')
    expect(document.body.classList.contains('nav-open')).toBe(false)
  })
})

describe('public landing route architecture', () => {
  it('exposes dedicated top-level routes for transparency pages', () => {
    const paths = landingRouter.getRoutes().map((route) => route.path)

    expect(paths).toContain('/')
    expect(paths).toContain('/status')
    expect(paths).toContain('/our-commitment')
    expect(paths).toContain('/contributors')
    expect(paths).toContain('/ecosystem')
    expect(paths).toContain('/provider-requests')
  })

  it('renders route-focused navigation links in the header', () => {
    const wrapper = mount(SiteHeader, {
      global: {
        stubs: {
          RouterLink: routerLinkStub,
        },
      },
    })
    const labels = wrapper.findAll('.nav-links a').map((item) => item.text())

    expect(labels).toEqual([
      'Home',
      'Status',
      'Our Commitment',
      'Contributors',
      'Ecosystem',
      'Provider Requests',
    ])
  })
})

describe('public landing status page', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads safe public status summaries from the backend endpoint', async () => {
    const responsePayload = {
      status: 'ok',
      overall: 'healthy',
      message: 'UAH API is running',
      timestamp: '2026-04-22T12:00:00Z',
      service_summaries: [
        { service: 'backend', status: 'healthy', summary: 'API process responding.' },
      ],
      services: {
        backend: {
          status: 'healthy',
          summary: 'API process responding.',
          name: 'UAH',
          version: '1.0.0',
        },
      },
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(responsePayload),
      })
    )

    const wrapper = mount(PublicStatusPage, {
      global: {
        stubs: {
          RouterLink: routerLinkStub,
        },
      },
    })
    await nextTick()
    await Promise.resolve()
    await nextTick()

    expect(global.fetch).toHaveBeenCalledWith('/api/status')
    expect(wrapper.text()).toContain('Public status overview')
    expect(wrapper.text()).toContain('API process responding.')
  })
})
