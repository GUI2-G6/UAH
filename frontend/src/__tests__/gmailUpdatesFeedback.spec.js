import { beforeEach, describe, expect, it, vi } from 'vitest'

const authMocks = vi.hoisted(() => ({
  authedFetch: vi.fn(),
  getCurrentUser: vi.fn(() => ({ id: 5 })),
}))

vi.mock('@/lib/auth.js', () => ({
  authedFetch: authMocks.authedFetch,
  getCurrentUser: authMocks.getCurrentUser,
}))

import { createGmailFeedback, writeGmailScanCache } from '@/lib/gmailUpdates.js'

describe('gmailUpdates feedback utilities', () => {
  beforeEach(() => {
    authMocks.authedFetch.mockReset()
    localStorage.clear()
  })

  it('normalizes body_preview into cached results', () => {
    const record = writeGmailScanCache({
      results: [
        {
          source_id: 'abc',
          body_preview: 'Body with extra context',
        },
      ],
    })
    expect(record.results[0].body_preview).toBe('Body with extra context')
  })

  it('maps action_required status bucket in cached scan results', () => {
    const record = writeGmailScanCache({
      results: [
        {
          source_id: 'needs-action-1',
          detected_status: 'action_required',
        },
      ],
    })
    expect(record.results[0].status_bucket).toBe('action_required')
    expect(record.summary.action_required).toBe(1)
  })

  it('normalizes canonical company and Gmail cluster metadata in cached scan results', () => {
    const record = writeGmailScanCache({
      results: [
        {
          source_id: 'leader-1',
          detected_status: 'applied',
          canonical_company_hint: 'Expedia Group',
          company_hint: 'Ripplematch',
          cluster_id: 'c1deadbeef',
          cluster_size: 2,
          cluster_rank: 0,
          cluster_leader_source_id: 'leader-1',
          application_chain_key: 'expedia|intern|stub',
        },
      ],
    })
    expect(record.results[0].canonical_company_hint).toBe('Expedia Group')
    expect(record.results[0].display_company).toBe('Expedia Group')
    expect(record.results[0].company_hint).toBe('Ripplematch')
    expect(record.results[0].cluster_id).toBe('c1deadbeef')
    expect(record.results[0].cluster_size).toBe(2)
    expect(record.results[0].cluster_rank).toBe(0)
    expect(record.results[0].cluster_leader_source_id).toBe('leader-1')
    expect(record.results[0].application_chain_key).toBe('expedia|intern|stub')
  })

  it('posts feedback payload to backend endpoint', async () => {
    authMocks.authedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ feedback: { id: 1, triage_label: 'not_relevant' } }),
    })

    const response = await createGmailFeedback({ source_id: 'abc', triage_label: 'not_relevant' })

    expect(response.id).toBe(1)
    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/integrations/gmail/feedback', expect.any(Object))
  })
})
