import { readFileSync } from 'node:fs'

import { mount } from '@vue/test-utils'
import { describe, expect, it, vi, afterEach } from 'vitest'

import Footer from '@/components/Footer.vue'
import { showToast } from '@/services/toastService.js'

vi.mock('@/services/toastService.js', () => ({
  showToast: vi.fn(),
}))

describe('frontend footer external-landing bridge', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens landing transparency destinations in a new tab and emits a toast', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => ({}))
    const wrapper = mount(Footer)

    await wrapper.get('[data-test="footer-link-status"]').trigger('click')

    expect(openSpy).toHaveBeenCalledWith('https://uahapp.com/status', '_blank', 'noopener,noreferrer')
    expect(showToast).toHaveBeenCalledWith('Status opened in a new tab.', 'success')
  })
})

describe('legacy public route compatibility', () => {
  it('turns legacy public views into lightweight bridge pages', () => {
    const statusSource = readFileSync('src/views/Status.vue', 'utf8')
    const commitmentSource = readFileSync('src/views/Our-Commitment.vue', 'utf8')
    const contributorsSource = readFileSync('src/views/Contributors.vue', 'utf8')

    expect(statusSource).toContain('This page moved to the public landing')
    expect(commitmentSource).toContain('This page moved to the public landing')
    expect(contributorsSource).toContain('This page moved to the public landing')
  })
})
