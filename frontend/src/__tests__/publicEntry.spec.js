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

    expect(wrapper.text()).toContain('Beta access is invite-only')
    expect(wrapper.text()).toContain('Already have an account?')
    expect(wrapper.text()).toContain('Request beta access')
    expect(wrapper.text()).toContain('Need the full overview first?')
    expect(wrapper.text()).toContain('Open the public landing page')
  })
})

describe('frontend footer public links', () => {
  it('keeps support mail contact while surfacing landing transparency links', () => {
    const footer = mount(Footer, globalMountOptions)

    expect(footer.get('a[href^="mailto:"]').attributes('href')).toBe('mailto:support@uahapp.com')
    expect(footer.text()).toContain('Status')
    expect(footer.text()).toContain('Privacy Policy')
    expect(footer.text()).toContain('Terms')
    expect(footer.text()).toContain('Contributors')
    expect(footer.text()).toContain('Ecosystem')
    expect(footer.text()).toContain('Provider Requests')
  })
})
