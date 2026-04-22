import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('vue-router', () => ({
  useRouter: () => ({
    back: vi.fn(),
    push: vi.fn(),
  }),
}))

vi.mock('@/lib/auth', () => ({
  getCurrentUser: () => null,
}))

import Footer from '@/components/Footer.vue'
import Landing from '@/views/Landing.vue'
import OurCommitment from '@/views/Our-Commitment.vue'

const globalMountOptions = {
  global: {
    stubs: {
      RouterLink: {
        props: ['to'],
        template: '<a :href="typeof to === \'string\' ? to : String(to)"><slot /></a>',
      },
    },
  },
}

describe('guest entry experience', () => {
  it('clearly separates beta access actions from the public product overview', () => {
    const wrapper = mount(Landing, globalMountOptions)

    expect(wrapper.text()).toContain('Already invited to the beta?')
    expect(wrapper.text()).toContain('Need the full overview first?')
    expect(wrapper.text()).toContain('Open the public landing page')
  })
})

describe('frontend mail routing', () => {
  it('uses privacy, team, legal, accessibility, and support inboxes in the public-facing app pages', () => {
    const commitment = mount(OurCommitment, globalMountOptions)
    const footer = mount(Footer, globalMountOptions)

    const mailtoLinks = commitment.findAll('a[href^="mailto:"]').map((link) => link.attributes('href'))

    expect(mailtoLinks).toContain('mailto:privacy@uahapp.com')
    expect(mailtoLinks).toContain('mailto:team@uahapp.com')
    expect(mailtoLinks).toContain('mailto:legal@uahapp.com')
    expect(mailtoLinks).toContain('mailto:accessibility@uahapp.com')
    expect(footer.get('a[href^="mailto:"]').attributes('href')).toBe('mailto:support@uahapp.com')
  })
})
