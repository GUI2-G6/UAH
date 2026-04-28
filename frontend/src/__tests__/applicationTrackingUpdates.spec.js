import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'

const authMocks = vi.hoisted(() => ({
  authedFetch: vi.fn(),
  getCurrentUser: vi.fn(),
}))

const gmailMocks = vi.hoisted(() => ({
  readGmailScanCache: vi.fn(),
  resolveGmailConnectionStatus: vi.fn(),
  runGmailScan: vi.fn(),
  subscribeGmailUpdates: vi.fn(),
  summarizeGmailResults: vi.fn(),
  listGmailSuppressions: vi.fn(),
  createGmailSuppression: vi.fn(),
  removeGmailSuppression: vi.fn(),
}))

vi.mock('@/lib/auth.js', () => ({
  authedFetch: authMocks.authedFetch,
  getCurrentUser: authMocks.getCurrentUser,
}))

vi.mock('@/lib/gmailUpdates.js', () => ({
  readGmailScanCache: gmailMocks.readGmailScanCache,
  resolveGmailConnectionStatus: gmailMocks.resolveGmailConnectionStatus,
  runGmailScan: gmailMocks.runGmailScan,
  subscribeGmailUpdates: gmailMocks.subscribeGmailUpdates,
  summarizeGmailResults: gmailMocks.summarizeGmailResults,
  listGmailSuppressions: gmailMocks.listGmailSuppressions,
  createGmailSuppression: gmailMocks.createGmailSuppression,
  removeGmailSuppression: gmailMocks.removeGmailSuppression,
}))

const cardStub = defineComponent({
  name: 'CardStub',
  template: '<div><slot name="header"></slot><slot></slot></div>',
})

const applicationStub = defineComponent({
  name: 'ApplicationStub',
  props: ['application'],
  template: '<div class="app-stub">{{ application?.subject || "" }}</div>',
})

import ApplicationView from '@/views/Application.vue'
import { runGmailScan } from '@/lib/gmailUpdates.js'

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('Application tracking page updates', () => {
  beforeEach(() => {
    authMocks.authedFetch.mockReset()
    authMocks.getCurrentUser.mockReset()
    gmailMocks.readGmailScanCache.mockReset()
    gmailMocks.resolveGmailConnectionStatus.mockReset()
    gmailMocks.runGmailScan.mockReset()
    gmailMocks.subscribeGmailUpdates.mockReset()
    gmailMocks.summarizeGmailResults.mockReset()
    gmailMocks.listGmailSuppressions.mockReset()
    gmailMocks.createGmailSuppression.mockReset()
    gmailMocks.removeGmailSuppression.mockReset()

    authMocks.getCurrentUser.mockReturnValue({
      id: 7,
      email: 'trent@example.com',
      gmail_refresh_token: 'token',
    })
    gmailMocks.readGmailScanCache.mockReturnValue(null)
    gmailMocks.resolveGmailConnectionStatus.mockResolvedValue(true)
    gmailMocks.subscribeGmailUpdates.mockReturnValue(() => {})
    gmailMocks.summarizeGmailResults.mockReturnValue({
      applied: 0,
      interview: 0,
      offer: 0,
      rejection: 0,
    })
    gmailMocks.listGmailSuppressions.mockResolvedValue([])
    authMocks.authedFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ tracked_applications: [] }),
    })
    gmailMocks.runGmailScan.mockResolvedValue({
      results: [],
      fetched_at: '2026-01-01T00:00:00.000Z',
      scan_scope: { applied_job_candidates: 0 },
    })
  })

  it('sends explicit scan mode when scanning for saved tracked applications', async () => {
    const wrapper = mount(ApplicationView, {
      global: {
        stubs: {
          Card: cardStub,
          Application: applicationStub,
        },
        mocks: {
          $router: { push: vi.fn() },
        },
      },
    })
    await flushPromises()

    await wrapper.vm.scanNow('saved')

    expect(runGmailScan).toHaveBeenCalledWith(expect.objectContaining({ scan_mode: 'saved' }))
  })

  it('shows all statuses option and defaults to it', async () => {
    const wrapper = mount(ApplicationView, {
      global: {
        stubs: {
          Card: cardStub,
          Application: applicationStub,
        },
        mocks: {
          $router: { push: vi.fn() },
        },
      },
    })
    await flushPromises()

    const options = wrapper.findAll('#app-filter option').map((node) => node.text())
    expect(options).toContain('All statuses')
    expect(wrapper.vm.selectedStatusFilter).toBe('all')
  })
})
