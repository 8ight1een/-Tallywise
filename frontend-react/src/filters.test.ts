import { describe, expect, it } from 'vitest'
import { localDate } from './format'
import { filters, moveMonth, validMonth } from './filters'

describe('validMonth', () => {
  it('保留合法月份', () => {
    expect(validMonth('2026-11')).toBe('2026-11')
  })

  it('非法值回落到当月', () => {
    expect(validMonth('2026-13')).toBe(localDate().slice(0, 7))
    expect(validMonth(null)).toBe(localDate().slice(0, 7))
  })
})

describe('moveMonth', () => {
  it('跨年移动', () => {
    expect(moveMonth('2026-01', -1)).toBe('2025-12')
    expect(moveMonth('2026-12', 1)).toBe('2027-01')
  })

  it('越界时保持不变', () => {
    expect(moveMonth('0001-01', -1)).toBe('0001-01')
  })
})

describe('filters', () => {
  it('解析合法筛选条件', () => {
    const result = filters(
      new URLSearchParams('month=2025-03&q=咖啡&money_type=支出&account_id=12'),
    )
    expect(result).toEqual({
      month: '2025-03',
      q: '咖啡',
      money_type: '支出',
      account_id: '12',
    })
  })

  it('丢弃非法的类型与账户', () => {
    const result = filters(new URLSearchParams('money_type=其他&account_id=0'))
    expect(result.money_type).toBe('')
    expect(result.account_id).toBe('')
  })
})
