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
import ResumeReviewModal from '@/components/ResumeReviewModal.vue'

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

describe('applicant profile field bindings', () => {
  beforeEach(() => {
    authMocks.authedFetch.mockReset()
  })

  it('loads and saves middle/legal/preferred name fields', () => {
    const ctx = {
      profiles: [{ id: 3, name: 'Default' }],
      activeProfileId: 3,
      applicantEditingField: 'firstName',
      applicantSavingField: 'firstName',
      firstName: '',
      middleName: '',
      lastName: '',
      fullLegalName: '',
      preferredName: '',
      suffix: '',
      appEmail: '',
      phone: '',
      linkedin: '',
      portfolio: '',
      streetAddress: '',
      city: '',
      appState: '',
      zip: '',
      summary: '',
      workAuth: '',
      requiresSponsorship: '',
      degree: '',
      major: '',
      university: '',
      gradYear: '',
      gpa: '',
      yearsExperience: '',
      jobTitle: '',
      skillsText: '',
      certificationsText: '',
      professionalLinksText: '',
      educationHistoryText: '',
      employmentHistoryText: '',
      loadedEducationHistoryText: '',
      loadedEmploymentHistoryText: '',
      demographicGender: '',
      demographicEthnicity: '',
      veteranStatus: '',
      disabilityStatus: '',
      californiaResident: '',
      activeTab: 'resumes',
      syncApplicantSavedSignature: vi.fn(),
      startJobInfoSession: vi.fn(),
      normalizedTextValue: ResumesView.methods.normalizedTextValue,
    }

    ResumesView.methods.populateFormFromProfile.call(ctx, {
      id: 3,
      first_name: 'Trent',
      middle_name: 'G',
      last_name: 'Brown',
      full_legal_name: 'Trent G Brown',
      preferred_name: 'TB',
      suffix: 'Jr',
      email: 'trent@example.com',
      phone: '(339) 440-0642',
    })

    expect(ctx.middleName).toBe('G')
    expect(ctx.fullLegalName).toBe('Trent G Brown')
    expect(ctx.preferredName).toBe('TB')
    expect(ctx.suffix).toBe('Jr')

    const payload = ResumesView.methods.buildProfilePayload.call(ctx)
    expect(payload).toEqual(expect.objectContaining({
      first_name: 'Trent',
      middle_name: 'G',
      last_name: 'Brown',
      full_legal_name: 'Trent G Brown',
      preferred_name: 'TB',
      suffix: 'Jr',
    }))
  })

  it('blocks deleting the only remaining profile', async () => {
    const ctx = {
      profiles: [{ id: 3, name: 'Default', is_active: true }],
      activeProfileId: 3,
      saveStatus: { type: '', message: '' },
      refreshProfileList: vi.fn(),
      loadProfileData: vi.fn(),
      publishDebugState: vi.fn(),
    }

    await ResumesView.methods.deleteProfile.call(ctx, 3)

    expect(authMocks.authedFetch).not.toHaveBeenCalled()
    expect(ctx.saveStatus).toEqual({
      type: 'error',
      message: 'Cannot delete your only profile.',
    })
  })

  it('allows deleting active profile when another profile exists', async () => {
    authMocks.authedFetch.mockResolvedValueOnce({ ok: true })
    const ctx = {
      profiles: [
        { id: 3, name: 'Default', is_active: true },
        { id: 4, name: 'Internships', is_active: false },
      ],
      activeProfileId: 3,
      saveStatus: { type: '', message: '' },
      refreshProfileList: vi.fn(async function refresh() {
        this.profiles = [{ id: 4, name: 'Internships', is_active: true }]
      }),
      loadProfileData: vi.fn(),
      publishDebugState: vi.fn(),
    }

    await ResumesView.methods.deleteProfile.call(ctx, 3)

    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/applicant-profile/3', { method: 'DELETE' })
    expect(ctx.refreshProfileList).toHaveBeenCalled()
    expect(ctx.loadProfileData).toHaveBeenCalledWith(4)
    expect(ctx.saveStatus).toEqual({
      type: 'success',
      message: 'Profile deleted.',
    })
  })
})

describe('resume review modal schema defaults', () => {
  it('keeps middle_name in normalized personal info when schema is absent', () => {
    const ctx = {
      personalFields: [],
      skillFields: [],
      ...ResumeReviewModal.methods,
    }

    const normalized = ResumeReviewModal.methods.normalizeDraft.call(ctx, {
      personal_info: {
        first_name: 'Trent',
        middle_name: 'G',
        last_name: 'Brown',
      },
    })

    expect(Object.keys(normalized.personal_info)).toContain('middle_name')
    expect(normalized.personal_info.middle_name).toBe('G')
  })
})
