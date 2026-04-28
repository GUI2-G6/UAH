import { describe, expect, it } from 'vitest'

import { messageFromApiFailure } from '../apiErrorMessage.js'

function mockRes(status) {
  return { status, headers: { get: () => null } }
}

describe('messageFromApiFailure', () => {
  it('describes 429 with Retry-After in seconds', () => {
    const msg = messageFromApiFailure(
      { status: 429, headers: { get: (k) => (k === 'Retry-After' ? '30' : null) } },
      {}
    )
    expect(msg).toContain('30 second')
  })

  it('describes 429 with Retry-After in minutes when large', () => {
    const msg = messageFromApiFailure(
      { status: 429, headers: { get: (k) => (k === 'Retry-After' ? '120' : null) } },
      {}
    )
    expect(msg).toContain('2 minute')
  })

  it('falls back when 429 has no usable Retry-After', () => {
    const msg = messageFromApiFailure(mockRes(429), {})
    expect(msg.toLowerCase()).toContain('too many')
  })

  it('formats 422 array detail from FastAPI', () => {
    const msg = messageFromApiFailure(
      mockRes(422),
      { detail: [{ type: 'value_error', loc: ['body', 'email'], msg: 'Invalid email' }] }
    )
    expect(msg).toContain('Invalid email')
  })

  it('uses string detail for other statuses', () => {
    const msg = messageFromApiFailure(mockRes(400), { detail: '  Bad thing  ' })
    expect(msg).toBe('Bad thing')
  })

  it('handles network (status 0)', () => {
    const msg = messageFromApiFailure({ status: 0 }, null)
    expect(msg.toLowerCase()).toMatch(/connection/)
  })
})
