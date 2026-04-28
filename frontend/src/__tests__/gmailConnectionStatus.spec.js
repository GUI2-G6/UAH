import { beforeEach, describe, expect, it, vi } from 'vitest'

const authMocks = vi.hoisted(() => ({
  authedFetch: vi.fn(),
  getCurrentUser: vi.fn(),
}))

vi.mock('@/lib/auth.js', () => ({
  authedFetch: authMocks.authedFetch,
  getCurrentUser: authMocks.getCurrentUser,
}))

import { resolveGmailConnectionStatus } from '@/lib/gmailUpdates.js'

describe('resolveGmailConnectionStatus', () => {
  beforeEach(() => {
    authMocks.authedFetch.mockReset()
    authMocks.getCurrentUser.mockReset()
  })

  it('uses integrations gmail service as canonical source', async () => {
    authMocks.authedFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ connected: true, status: 'connected' }),
    })

    const connected = await resolveGmailConnectionStatus(false)

    expect(connected).toBe(true)
    expect(authMocks.authedFetch).toHaveBeenCalledWith('/api/integrations/services/gmail')
  })

  it('falls back to current user token state when service lookup fails', async () => {
    authMocks.authedFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'unavailable' }),
    })
    authMocks.getCurrentUser.mockReturnValue({ gmail_refresh_token: 'present' })

    const connected = await resolveGmailConnectionStatus(false)

    expect(connected).toBe(true)
  })
})
