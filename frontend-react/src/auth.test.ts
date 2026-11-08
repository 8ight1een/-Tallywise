import { describe, expect, it } from 'vitest'
import { sessionReducer } from './auth'
import type { User } from './types'

const user: User = { id: 1, email: 'a@example.com', nickname: '小航' }

describe('sessionReducer', () => {
  it('check 进入检查中', () => {
    expect(sessionReducer({ status: 'guest' }, { type: 'check' })).toEqual({
      status: 'checking',
    })
  })

  it('user 携带用户信息', () => {
    expect(sessionReducer({ status: 'checking' }, { type: 'user', user })).toEqual({
      status: 'user',
      user,
    })
  })

  it('error 保留原因', () => {
    expect(
      sessionReducer({ status: 'checking' }, { type: 'error', message: '网络错误' }),
    ).toEqual({ status: 'error', message: '网络错误' })
  })

  it('guest 清除会话', () => {
    expect(sessionReducer({ status: 'user', user }, { type: 'guest' })).toEqual({
      status: 'guest',
    })
  })
})
