import { describe, expect, it } from 'vitest'
import { amount, localDate } from './format'

describe('amount', () => {
  it('保留两位小数并加千分位', () => {
    expect(amount('1234.5')).toBe('1,234.50')
    expect(amount(0)).toBe('0.00')
  })
})

describe('localDate', () => {
  it('返回本地日期', () => {
    expect(localDate()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})
