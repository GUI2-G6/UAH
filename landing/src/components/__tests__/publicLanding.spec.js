import { readFileSync } from 'node:fs'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import BetaAccess from '../BetaAccess.vue'
import BrowserExtensionPage from '../../pages/BrowserExtensionPage.vue'
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
  it('keeps direct mail routing for partnerships/footer while beta access and wishlist use internal submit', () => {
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

    expect(beta.get('form.access-form').exists()).toBe(true)
    expect(beta.get('button[type="submit"]').text()).toContain('Submit request')
    expect(partners.get('.partner-cta .button').attributes('href')).toBe(
      'mailto:partners@uahapp.com?subject=UAH Partnership Inquiry'
    )
    expect(partners.text()).toContain('partners@uahapp.com')
    expect(wishlist.get('form').attributes('action')).toBeUndefined()
    expect(footerMailtoLinks).toContain('mailto:team@uahapp.com')
    expect(footerMailtoLinks).toContain('mailto:press@uahapp.com')
  })

  it('submits wishlist feedback through the public landing-feedback API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ message: 'Thanks — we received your feedback.' }),
      })
    )

    const wishlist = mount(WishlistForm)
    await wishlist.get('#email').setValue('visitor@example.com')
    await wishlist.get('form').trigger('submit.prevent')

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/public/landing-feedback',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    )
    const rawBody = global.fetch.mock.calls[0][1].body
    const body = JSON.parse(rawBody)
    expect(body.email).toBe('visitor@example.com')
    expect(body.source_surface).toBe('landing_wishlist')
    vi.unstubAllGlobals()
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
    document.documentElement.style.removeProperty('--site-header-height')
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

  it('publishes a dynamic site header height CSS variable for mobile drawer offsets', async () => {
    window.innerWidth = 800

    const wrapper = mountHeader()
    const header = wrapper.get('.site-header').element
    header.getBoundingClientRect = () => ({ width: 360, height: 86, top: 0, left: 0, right: 360, bottom: 86 })
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    const measuredHeight = document.documentElement.style.getPropertyValue('--site-header-height').trim()
    expect(measuredHeight).toMatch(/^\d+px$/)

    await wrapper.get('.nav-toggle').trigger('click')
    await nextTick()
    const openHeight = document.documentElement.style.getPropertyValue('--site-header-height').trim()
    expect(openHeight).toMatch(/^\d+px$/)
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
    expect(paths).toContain('/browser-extension')
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
      'Extension (alpha)',
      'Provider Requests',
    ])
  })

  it('enters compact desktop nav state in intermediate widths', async () => {
    window.innerWidth = 1180
    const wrapper = mountHeader()
    await nextTick()

    expect(wrapper.get('.nav-inner').classes()).toContain('is-compact-desktop')

    window.innerWidth = 1400
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect(wrapper.get('.nav-inner').classes()).not.toContain('is-compact-desktop')
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

describe('public extension page', () => {
  it('states alpha limitations and links to install guidance', () => {
    const wrapper = mount(BrowserExtensionPage)
    const links = wrapper.findAll('a').map((item) => item.attributes('href'))

    expect(wrapper.text()).toContain('highly alpha state')
    expect(wrapper.text()).toContain('very limited functionality')
    expect(links).toContain('/downloads/uah-browser-extension-alpha.zip')
    expect(links).toContain('https://github.com/GUI2-G6/UAH/blob/dev/docs/BROWSER_EXTENSION_CHROME_INSTALL.md')
  })
})
