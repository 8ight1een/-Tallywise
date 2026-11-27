import { json, request } from './api'
import { localDate } from './format'
import type { Catalog, MoneyType, TransactionInput } from './types'

export type DraftResult = {
  status: 'ready' | 'needs_input'
  fields: {
    account_id: number | null
    category_id: number | null
    money: string | null
    money_type: MoneyType | null
    description: string | null
    transaction_date: string | null
    question: string | null
  }
  transaction: TransactionInput | null
  issues: string[]
}

export type BatchDraftResult = {
  drafts: DraftResult[]
  warnings: string[]
  prompt_version: string
}

export type EditableDraft = Omit<TransactionInput, 'money_type'> & {
  money_type: MoneyType | ''
}
export type PendingSave = { key: string; payload: TransactionInput }

export function toEditable(result: DraftResult): EditableDraft {
  const fields = result.transaction ?? result.fields
  return {
    account_id: fields.account_id ?? 0,
    category_id: fields.category_id ?? 0,
    money: fields.money ?? '',
    money_type: fields.money_type ?? '',
    description: fields.description ?? '',
    transaction_date: fields.transaction_date ?? '',
  }
}

export function validDate(value: string) {
  if (!/^(?!0000)\d{4}-(0[1-9]|1[0-2])-\d{2}$/.test(value)) return false
  const [year, month, day] = value.split('-').map(Number)
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0)
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  return day >= 1 && day <= days[month - 1]
}

export function buildTransaction(draft: EditableDraft, catalog: Catalog): TransactionInput {
  if (draft.money_type !== '收入' && draft.money_type !== '支出')
    throw new Error('请选择收入或支出')
  if (!catalog.accounts.some((item) => item.id === draft.account_id))
    throw new Error('请选择有效账户')
  if (!catalog.categories.some((item) =>
    item.id === draft.category_id && item.money_type === draft.money_type))
    throw new Error('请选择与收支类型匹配的分类')
  const money = draft.money.trim()
  if (!/^\d{1,7}(?:\.\d{1,2})?$/.test(money) || Number(money) <= 0)
    throw new Error('金额必须大于 0，最多 7 位整数和 2 位小数')
  if (!validDate(draft.transaction_date)) throw new Error('请填写有效日期')
  const description = draft.description?.trim() || null
  if (description && [...description].length > 250) throw new Error('备注不能超过 250 字')
  return { ...draft, money_type: draft.money_type, money, description }
}

export function requestDrafts(text: string, signal: AbortSignal) {
  return request<BatchDraftResult>('/ai/transaction-drafts', {
    ...json('POST', { text: text.trim(), reference_date: localDate() }),
    signal,
  })
}

const storageKey = (userId: number) => `tallywise:ai-pending:v1:${userId}`

export function readPending(userId: number): PendingSave | null {
  try {
    const raw = sessionStorage.getItem(storageKey(userId))
    if (!raw) return null
    const value = JSON.parse(raw) as PendingSave
    const p = value?.payload
    if (typeof value?.key !== 'string' || !value.key || value.key.length > 200 || !p)
      return null
    if (!Number.isInteger(p.account_id) || !Number.isInteger(p.category_id) ||
      p.account_id <= 0 || p.category_id <= 0 || typeof p.money !== 'string' ||
      (p.money_type !== '收入' && p.money_type !== '支出') ||
      typeof p.transaction_date !== 'string' || !validDate(p.transaction_date) ||
      (p.description !== null && typeof p.description !== 'string')) return null
    return value
  } catch {
    return null
  }
}

export function rememberPending(userId: number, pending: PendingSave) {
  sessionStorage.setItem(storageKey(userId), JSON.stringify(pending))
}

export function clearPending(userId: number) {
  try {
    sessionStorage.removeItem(storageKey(userId))
    return true
  } catch {
    return false
  }
}
