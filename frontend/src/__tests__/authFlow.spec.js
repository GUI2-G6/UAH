import { readFileSync } from 'node:fs'

import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import Landing from '@/views/Landing.vue'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Signup from '@/views/Signup.vue'

const routerPush = vi.fn()
const routerReplace = vi.fn()

const componentMountOptions = {
  global: {
    stubs: {
      RouterLink: {
        props: ['to'],
        template: '<a :href="typeof to === \'string\' ? to : String(to)"><slot /></a>',
      },
      SecretInput: {
        props: ['modelValue'],
        emits: ['update:modelValue'],
        template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
      },
    },
    mocks: {
      $router: {
        push: routerPush,
        replace: routerReplace,
      },
      $route: {
        query: {},
        path: '/login',
      },
    },
  },
}

describe('unauthenticated gateway chooser', () => {
  it('makes invite-only beta registration and access requests obvious', () => {
    const wrapper = mount(Landing, componentMountOptions)

    expect(wrapper.text()).toContain('Beta access is invite-only')
    expect(wrapper.text()).toContain('Already have an account?')
    expect(wrapper.text()).toContain('Request beta access')
  })
})

describe('login clarity', () => {
  it('explains that Google only works after linking it in Settings and offers a way back', async () => {
    const wrapper = mount(Login, componentMountOptions)

    expect(wrapper.text()).toContain('linked it later in Settings')
    expect(wrapper.text()).toContain('Back to access options')

    await wrapper.get('.landing-btn').trigger('click')

    expect(routerPush).toHaveBeenCalledWith('/landing')
  })
})

describe('register clarity', () => {
  it('removes live Google signup, explains invite-only beta access, and offers an access request route', async () => {
    const wrapper = mount(Register, componentMountOptions)

    expect(wrapper.text()).toContain('invite-only beta')
    expect(wrapper.text()).toContain('Request beta access')
    expect(wrapper.text()).toContain('link Google later from Settings')
    expect(wrapper.text()).not.toContain('Continue with Google')

    await wrapper.get('.landing-btn').trigger('click')

    expect(routerPush).toHaveBeenCalledWith('/landing')
  })
})

describe('legacy signup routing', () => {
  it('keeps the legacy signup route public and styled like the other auth pages', () => {
    const routerSource = readFileSync('src/router/index.js', 'utf8')
    const appSource = readFileSync('src/App.vue', 'utf8')
    const signupSource = readFileSync('src/views/Signup.vue', 'utf8')

    expect(routerSource).toContain("'/signup'")
    expect(appSource).toContain("'/signup'")
    expect(signupSource).toContain('Back to access options')
  })

  it('lets the legacy signup page guide people to register instead of acting like a trap', async () => {
    const wrapper = mount(Signup, componentMountOptions)

    expect(wrapper.text()).toContain('Create account')
    expect(wrapper.text()).toContain('Back to access options')

    await wrapper.get('.submit-btn').trigger('click')

    expect(routerPush).toHaveBeenCalledWith('/register')
  })
})

describe('settings sign-in methods copy', () => {
  it('describes Google as an opt-in connection users add after account creation', () => {
    const settingsSource = readFileSync('src/views/Settings.vue', 'utf8')

    expect(settingsSource).toContain('After you create your account')
    expect(settingsSource).toMatch(/use Google to\s+sign in later/)
    expect(settingsSource).toContain('Export My Data')
    expect(settingsSource).toContain('/api/account/export/reauth')
  })
})
