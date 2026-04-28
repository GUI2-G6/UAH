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
