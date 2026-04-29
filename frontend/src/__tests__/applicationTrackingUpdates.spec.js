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
  removeGmailSuppression: vi.fn(),
  createGmailFeedback: vi.fn(),
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
  removeGmailSuppression: gmailMocks.removeGmailSuppression,
  createGmailFeedback: gmailMocks.createGmailFeedback,
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
    gmailMocks.removeGmailSuppression.mockReset()
    gmailMocks.createGmailFeedback.mockReset()

    authMocks.getCurrentUser.mockReturnValue({
      id: 7,
      email: 'trent@example.com',
      gmail_refresh_token: 'token',
    })
    gmailMocks.readGmailScanCache.mockReturnValue(null)
    gmailMocks.resolveGmailConnectionStatus.mockResolvedValue(true)
    gmailMocks.subscribeGmailUpdates.mockReturnValue(() => {})
    gmailMocks.summarizeGmailResults.mockReturnValue({
      action_required: 0,
      applied: 0,
      interview: 0,
      offer: 0,
      rejection: 0,
    })
    gmailMocks.listGmailSuppressions.mockResolvedValue([])
    gmailMocks.createGmailFeedback.mockResolvedValue({ id: 1, override_status: 'offer' })
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
    expect(options).toContain('Action Required')
    expect(options).toContain('Not moving forward')
    expect(wrapper.vm.selectedStatusFilter).toBe('all')
  })

  it('saves manual status override for a found email', async () => {
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
    wrapper.vm.applications = [{
      source_id: 'gmail-1',
      subject: 'Application update',
      from: 'Recruiting <jobs@example.com>',
      detected_status: 'unknown',
      status_bucket: 'unknown',
      company_hint: 'Example Co',
      sender_domain: 'example.com',
      subject_key: 'application update',
      company_key: 'example co',
      thread_key: 'example.com|application update|example co',
    }]

    await wrapper.vm.setManualStatus(wrapper.vm.feedItems[0], 'offer')

    expect(gmailMocks.createGmailFeedback).toHaveBeenCalledWith(expect.objectContaining({
      source_id: 'gmail-1',
      triage_label: 'relevant',
      override_status: 'offer',
    }))
    expect(wrapper.vm.applications[0].detected_status).toBe('offer')
    expect(wrapper.vm.applications[0].status_bucket).toBe('offer')
    expect(wrapper.vm.applications[0].manual_override_applied).toBe(true)
  })

  it('marks an update as not relevant and removes matching rows from current list', async () => {
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
    wrapper.vm.applications = [
      {
        source_id: 'gmail-1',
        subject: 'Additional Information Needed',
        from: 'Careers <do-not-reply@candidatecare.com>',
        detected_status: 'action_required',
        status_bucket: 'action_required',
        sender_domain: 'candidatecare.com',
        subject_key: 'additional information needed',
        company_key: 'granite telecommunications',
        thread_key: 'candidatecare.com|additional information needed|granite telecommunications',
      },
      {
        source_id: 'gmail-2',
        subject: 'Additional Information Needed',
        from: 'Careers <do-not-reply@candidatecare.com>',
        detected_status: 'action_required',
        status_bucket: 'action_required',
        sender_domain: 'candidatecare.com',
        subject_key: 'additional information needed',
        company_key: 'granite telecommunications',
        thread_key: 'candidatecare.com|additional information needed|granite telecommunications',
      },
    ]
    gmailMocks.createGmailFeedback.mockResolvedValueOnce({ id: 3, triage_label: 'not_relevant' })

    await wrapper.vm.setManualStatus(wrapper.vm.feedItems[0], 'not_relevant')

    expect(gmailMocks.createGmailFeedback).toHaveBeenCalledWith(expect.objectContaining({
      source_id: 'gmail-1',
      triage_label: 'not_relevant',
    }))
    expect(wrapper.vm.applications).toHaveLength(0)
  })

  it('shows high-priority section for action required updates', async () => {
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
    wrapper.vm.applications = [{
      source_id: 'gmail-action-1',
      subject: 'Additional Information Needed',
      from: 'Careers <do-not-reply@candidatecare.com>',
      detected_status: 'action_required',
      status_bucket: 'action_required',
      company_hint: 'Granite Telecommunications',
      sender_domain: 'candidatecare.com',
      subject_key: 'additional information needed',
      company_key: 'granite telecommunications',
      thread_key: 'candidatecare.com|additional information needed|granite telecommunications',
    }]
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('High Priority: Action Required')
    expect(wrapper.find('#action-required').exists()).toBe(true)
  })

  it('autosaves tracking when checkbox selection toggles on then archives from tracked list', async () => {
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
    wrapper.vm.applications = [{
      source_id: 'gmail-track-1',
      subject: 'Status update',
      from: 'Recruiting <jobs@example.com>',
      detected_status: 'unknown',
      status_bucket: 'unknown',
      company_hint: 'Example Co',
      sender_domain: 'example.com',
      subject_key: 'status update',
      company_key: 'example co',
      thread_key: 'example.com|status update|example co',
    }]

    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ created: 1, updated: 0 }) })
    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ tracked_applications: [{ id: 11, source_ref: 'gmail-track-1' }] }) })

    await wrapper.vm.toggleSelection(wrapper.vm.feedItems[0])
    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/applications/tracked/select', expect.any(Object))

    wrapper.vm.trackedApplications = [{ id: 11, source_ref: 'gmail-track-1', thread_key: 'example.com|status update|example co' }]
    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok' }) })
    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ tracked_applications: [], archived_applications: [] }) })
    await wrapper.vm.archiveTracked(11)
    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/applications/tracked/11', expect.any(Object))
  })

  it('clears only non-tracked rows in current filtered view', async () => {
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
    wrapper.vm.selectedStatusFilter = 'unknown'
    wrapper.vm.applications = [
      { source_id: 'a', subject: 'A', from: 'x', detected_status: 'unknown', status_bucket: 'unknown', thread_key: 'k1' },
      { source_id: 'b', subject: 'B', from: 'x', detected_status: 'unknown', status_bucket: 'unknown', thread_key: 'k2' },
      { source_id: 'c', subject: 'C', from: 'x', detected_status: 'offer', status_bucket: 'offer', thread_key: 'k3' },
    ]
    wrapper.vm.selectedKeys = { 'gmail:a': true }

    wrapper.vm.clearFilteredNonTracked()

    const ids = wrapper.vm.applications.map((item) => item.source_id)
    expect(ids).toEqual(['a', 'c'])
  })

  it('separates active and archived tracked applications with status filters', async () => {
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

    wrapper.vm.trackedApplications = [
      { id: 1, latest_status: 'offer', selection_state: 'active' },
      { id: 2, latest_status: 'unknown', selection_state: 'active' },
    ]
    wrapper.vm.archivedTrackedApplications = [
      { id: 3, latest_status: 'rejection', selection_state: 'archived' },
      { id: 4, latest_status: 'offer', selection_state: 'archived' },
    ]
    wrapper.vm.trackedStatusFilter = 'offer'
    wrapper.vm.archivedStatusFilter = 'rejection'
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.filteredTrackedApplications.map((row) => row.id)).toEqual([1])
    expect(wrapper.vm.filteredArchivedTrackedApplications.map((row) => row.id)).toEqual([3])
  })

  it('moves tracked scan rows out of active scan list immediately', async () => {
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

    wrapper.vm.applications = [{
      source_id: 'gmail-track-2',
      subject: 'Interview update',
      from: 'Recruiting <jobs@example.com>',
      detected_status: 'interview',
      status_bucket: 'interview',
      sender_domain: 'example.com',
      subject_key: 'interview update',
      company_key: 'example co',
      thread_key: 'example.com|interview update|example co',
    }]

    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ created: 1, updated: 0 }) })
    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ tracked_applications: [{ id: 12, source_ref: 'gmail-track-2', selection_state: 'active' }] }) })

    await wrapper.vm.toggleSelection(wrapper.vm.feedItems[0])

    expect(wrapper.vm.applications).toHaveLength(0)
  })

  it('archives and restores tracked applications', async () => {
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

    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok' }) })
    authMocks.authedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        tracked_applications: [{ id: 7, source_ref: 'gmail-7', selection_state: 'active' }],
        archived_applications: [{ id: 8, source_ref: 'gmail-8', selection_state: 'archived' }],
      }),
    })
    await wrapper.vm.archiveTracked(7)
    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/applications/tracked/7', expect.objectContaining({
      method: 'PATCH',
    }))

    wrapper.vm.archivedTrackedApplications = [{ id: 8, source_ref: 'gmail-8', thread_key: 'thread-8', company: 'Archived Co', job_title: 'SWE', latest_status: 'unknown' }]
    authMocks.authedFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ created: 0, updated: 1 }) })
    authMocks.authedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        tracked_applications: [{ id: 8, source_ref: 'gmail-8', selection_state: 'active' }],
        archived_applications: [],
      }),
    })
    await wrapper.vm.restoreTracked(wrapper.vm.archivedTrackedApplications[0])
    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/applications/tracked/select', expect.any(Object))
  })

  it('applies status glow class helpers for listings', async () => {
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

    expect(wrapper.vm.trackedGlowClassForStatus('offer')).toBe('status-glow-offer')
    expect(wrapper.vm.trackedGlowClassForStatus('application_received')).toBe('status-glow-applied')
  })
})
