import { useRef, useState, type FormEvent } from 'react'
import type { Catalog, MoneyType, Transaction, TransactionInput } from '../types'
import { errorText, json, request } from '../api'
import { localDate } from '../format'
import Modal from './Modal'
type Props = Catalog & {
  value?: Transaction
  onClose: () => void
  onSaved: () => void
}
export default function TransactionDialog({
  value,
  accounts,
  categories,
  onClose,
  onSaved,
}: Props) {
  const [draft, setDraft] = useState<TransactionInput>(() => ({
    account_id: value?.account_id ?? accounts[0]?.id ?? 0,
    category_id:
      value?.category_id ??
      categories.find((c) => c.money_type === '支出')?.id ??
      0,
    money: value?.money ?? '',
    money_type: value?.money_type ?? '支出',
    description: value?.description ?? '',
    transaction_date: value?.transaction_date ?? localDate(),
  }))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  const intent = useRef<{ body: string; key: string } | null>(null)
  function field<K extends keyof TransactionInput>(
    key: K,
    next: TransactionInput[K],
  ) {
    setDraft((previous) => ({ ...previous, [key]: next }))
  }
  function changeType(next: MoneyType) {
    setDraft((previous) => ({
      ...previous,
      money_type: next,
      category_id: categories.find((c) => c.money_type === next)?.id ?? 0,
    }))
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (
      !draft.account_id ||
      !categories.some(
        (c) => c.id === draft.category_id && c.money_type === draft.money_type,
      )
    ) {
      setError('请选择有效的账户和分类')
      return
    }
    if (
      !/^(?:0|[1-9]\d{0,6})(?:\.\d{1,2})?$/.test(draft.money) ||
      Number(draft.money) <= 0
    ) {
      setError('金额须大于0，最多7位整数和2位小数')
      return
    }
    await perform('save')
  }
  async function perform(action: 'save' | 'delete') {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError('')
    try {
      if (action === 'delete' && value)
        await request<void>('/transactions/' + value.id, json('DELETE'))
      else {
        const body = JSON.stringify({
          ...draft,
          description: draft.description?.trim() || null,
        })
        if (!intent.current || intent.current.body !== body)
          intent.current = { body, key: crypto.randomUUID() }
        await request<Transaction>(
          '/transactions' + (value ? '/' + value.id : ''),
          {
            method: value ? 'PUT' : 'POST',
            body,
            headers: value ? undefined : { 'Idempotency-Key': intent.current.key },
          },
        )
      }
      onSaved()
    } catch (reason) {
      setError(errorText(reason))
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  return (
    <Modal title={value ? '编辑记录' : '记一笔'} busy={busy} onClose={onClose}>
      <form className="form-body" onSubmit={save}>
        <fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0 }}>
          <div className="type-tabs">
            {(['支出', '收入'] as const).map((type) => (
              <button
                key={type}
                type="button"
                className={draft.money_type === type ? 'selected' : ''}
                aria-pressed={draft.money_type === type}
                onClick={() => changeType(type)}
              >
                {type}
              </button>
            ))}
          </div>
          <div className="amount-input">
            <label htmlFor="tx-money">金额</label>
            <div>
              <span>¥</span>
              <input
                id="tx-money"
                type="number"
                autoFocus
                required
                min="0.01"
                max="9999999.99"
                step="0.01"
                value={draft.money}
                onChange={(e) => field('money', e.currentTarget.value)}
              />
            </div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="tx-category">分类</label>
              <select
                id="tx-category"
                required
                value={draft.category_id || ''}
                onChange={(e) =>
                  field('category_id', Number(e.currentTarget.value))
                }
              >
                <option value="">请选择分类</option>
                {categories
                  .filter((c) => c.money_type === draft.money_type)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name_categories}
                    </option>
                  ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="tx-account">账户</label>
              <select
                id="tx-account"
                required
                value={draft.account_id || ''}
                onChange={(e) => field('account_id', Number(e.currentTarget.value))}
              >
                <option value="">请选择账户</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name_accounts}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field">
            <label htmlFor="tx-date">日期</label>
            <input
              id="tx-date"
              type="date"
              min="0001-01-01"
              max="9999-12-31"
              required
              value={draft.transaction_date}
              onChange={(e) => field('transaction_date', e.currentTarget.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="tx-description">备注 · 选填</label>
            <input
              id="tx-description"
              maxLength={250}
              value={draft.description ?? ''}
              onChange={(e) => field('description', e.currentTarget.value)}
            />
          </div>
          <p className="form-error" role="alert">
            {error}
          </p>
          <div className="form-bottom">
            {value && (
              <button
                className="secondary"
                type="button"
                onClick={() => {
                  if (window.confirm('确定删除这笔记录？')) void perform('delete')
                }}
              >
                删除记录
              </button>
            )}
            <button className="primary" type="submit">
              {busy ? '正在保存…' : '保存记录'}
            </button>
          </div>
        </fieldset>
      </form>
    </Modal>
  )
}
