import { useRef, useState, type FormEvent } from 'react'
import type { Account, Category, MoneyType } from '../types'
import { errorText, json, request } from '../api'
import Modal from './Modal'
export type EntityEditor = {
  kind: 'account' | 'category'
  value?: Account | Category
}
type Props = EntityEditor & { onClose: () => void; onSaved: () => void }
export default function EntityDialog({ kind, value, onClose, onSaved }: Props) {
  const account = kind === 'account'
  const [name, setName] = useState(
    value
      ? 'name_accounts' in value
        ? value.name_accounts
        : value.name_categories
      : '',
  )
  const [type, setType] = useState<MoneyType>(
    value && 'money_type' in value ? value.money_type : '支出',
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  const path =
    '/' + (account ? 'accounts' : 'categories') + (value ? '/' + value.id : '')
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!name.trim()) {
      setError('名称不能全是空格')
      return
    }
    await perform(value ? 'PUT' : 'POST')
  }
  async function perform(method: 'POST' | 'PUT' | 'DELETE') {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError('')
    try {
      const data = account
        ? { name_accounts: name.trim() }
        : { name_categories: name.trim(), money_type: type }
      await request(path, json(method, method === 'DELETE' ? undefined : data))
      onSaved()
    } catch (reason) {
      setError(errorText(reason))
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  return (
    <Modal
      title={(value ? '编辑' : '新增') + (account ? '账户' : '分类')}
      busy={busy}
      onClose={onClose}
    >
      <form className="form-body" onSubmit={save}>
        <fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0 }}>
          <div className="field">
            <label htmlFor="entity-name">名称</label>
            <input
              id="entity-name"
              autoFocus
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
            />
          </div>
          {!account && (
            <div className="field">
              <label htmlFor="entity-type">收支类型</label>
              <select
                id="entity-type"
                value={type}
                onChange={(e) => setType(e.currentTarget.value as MoneyType)}
              >
                <option>支出</option>
                <option>收入</option>
              </select>
            </div>
          )}
          <p className="form-error" role="alert">
            {error}
          </p>
          <div className="form-bottom">
            {value && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  if (window.confirm('确定删除？已有流水的项目不能删除。'))
                    void perform('DELETE')
                }}
              >
                删除
              </button>
            )}
            <button type="submit" className="primary">
              {busy ? '正在保存…' : '保存'}
            </button>
          </div>
        </fieldset>
      </form>
    </Modal>
  )
}
