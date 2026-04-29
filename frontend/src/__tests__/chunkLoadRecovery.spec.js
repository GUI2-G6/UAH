import { beforeEach, describe, expect, it } from 'vitest'

import { getChunkRecoveryAction, isChunkLoadFailure } from '@/lib/chunkLoadRecovery.js'

describe('chunkLoadRecovery', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
  })

  it('detects common dynamic import chunk failure signatures', () => {
    expect(isChunkLoadFailure(new TypeError('Failed to fetch dynamically imported module'))).toBe(true)
    expect(isChunkLoadFailure(new Error('ChunkLoadError: Loading chunk 17 failed.'))).toBe(true)
    expect(isChunkLoadFailure({ reason: { message: 'Loading chunk 55 failed' } })).toBe(true)
    expect(isChunkLoadFailure(new Error('Network Error'))).toBe(false)
  })

  it('returns reload once, then notify for the same route', () => {
    const first = getChunkRecoveryAction('/analytics')
    const second = getChunkRecoveryAction('/analytics')
    const otherRoute = getChunkRecoveryAction('/home')

    expect(first.action).toBe('reload')
    expect(second.action).toBe('notify')
    expect(otherRoute.action).toBe('reload')
  })
})

