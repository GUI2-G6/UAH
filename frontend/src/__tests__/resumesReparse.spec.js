import { beforeEach, describe, expect, it, vi } from 'vitest'

const authMocks = vi.hoisted(() => ({
  authedFetch: vi.fn(),
  getCurrentUser: vi.fn(),
  setCurrentUser: vi.fn(),
}))

vi.mock('@/lib/auth.js', () => ({
  authedFetch: authMocks.authedFetch,
  getCurrentUser: authMocks.getCurrentUser,
  setCurrentUser: authMocks.setCurrentUser,
}))

vi.mock('@/lib/debugDiagnostics', () => ({
  publishCurrentPageDiagnostics: vi.fn(),
  clearCurrentPageDiagnostics: vi.fn(),
}))

vi.mock('@/services/toastService.js', () => ({
  showToast: vi.fn(),
}))

vi.mock('@/lib/validation.js', () => ({
  assertValidEmail: vi.fn(),
  buildMailtoHref: vi.fn(),
  buildPhoneHref: vi.fn(),
  inferPhoneCountry: vi.fn(),
  normalizePhone: vi.fn(),
}))

import ResumesView from '@/views/Resumes.vue'

describe('resume re-parse flow', () => {
  beforeEach(() => {
    authMocks.authedFetch.mockReset()
  })

  it('posts parse-async for an existing resume', async () => {
    authMocks.authedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: 99 }),
    })
    const pollParseJob = vi.fn()
    const publishDebugState = vi.fn()
    const ctx = {
      parseJobId: null,
      parseResumeId: null,
      parseStatus: null,
      parseStageLabel: '',
      parseError: null,
      parseJobMethod: null,
      uploadStep: 'confirm',
      pollParseJob,
      publishDebugState,
      apiErrorMessage: vi.fn(),
    }

    await ResumesView.methods.queueParseForResume.call(ctx, 42, 'cloud')

    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/resume/42/parse-async', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method: 'cloud' }),
    })
    expect(ctx.parseJobId).toBe(99)
    expect(ctx.parseResumeId).toBe(42)
    expect(ctx.parseJobMethod).toBe('cloud')
    expect(ctx.uploadStep).toBe('parsing')
    expect(pollParseJob).toHaveBeenCalled()
    expect(publishDebugState).toHaveBeenCalledWith('parse-started')
  })

  it('falls back from local to cloud when local parser is unavailable', async () => {
    const queueParseForResume = vi.fn().mockResolvedValue(undefined)
    const publishDebugState = vi.fn()
    const ctx = {
      parseMethod: 'local',
      isLocalParseMethodAvailable: false,
      parseJobId: null,
      parseResumeId: null,
      parseJobMethod: null,
      uploadStep: 'confirm',
      uploadError: null,
      showLibraryModal: true,
      reparseBusyId: null,
      queueParseForResume,
      publishDebugState,
    }

    await ResumesView.methods.startReparse.call(ctx, { id: 13 })

    expect(ctx.parseMethod).toBe('cloud')
    expect(queueParseForResume).toHaveBeenCalledWith(13, 'cloud')
    expect(ctx.reparseBusyId).toBe(null)
  })
})
