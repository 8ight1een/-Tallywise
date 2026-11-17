import type { FormEvent } from 'react'
import type { EditableDraft } from '../ai'
import type { Catalog, MoneyType } from '../types'
import Icon from './Icon'

type Props = {
  draft: EditableDraft
  catalog: Catalog
  issues: string[]
  busy: boolean
  locked: boolean
  disabled: boolean
  error: string
  onChange: (draft: EditableDraft) => void
  onSave: () => void
  onDiscard: () => void
}

export default function AiDraftCard({
  draft, catalog, issues, busy, locked, disabled, error, onChange, onSave, onDiscard,
}: Props) {
  function field<K extends keyof EditableDraft>(key: K, value: EditableDraft[K]) {
    onChange({ ...draft, [key]: value })
  }
  function changeType(money_type: MoneyType) {
    const keepCategory = catalog.categories.some((item) =>
      item.id === draft.category_id && item.money_type === money_type)
    onChange({ ...draft, money_type, category_id: keepCategory ? draft.category_id : 0 })
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSave()
  }
  return (
    <section className="panel ai-draft" aria-labelledby="ai-draft-title">
      <div className="ai-card-heading">
        <span className="ai-kicker">REVIEW YOUR ENTRY</span>
        <div className="ai-heading-row">
          <h2 id="ai-draft-title">{locked ? '等待确认提交结果' : '核对这一笔'}</h2>
          <span className="ai-badge">{locked ? '待确认' : '尚未入账'}</span>
        </div>
        <p>检查金额与归属，确认后才会写入账本。</p>
      </div>
      {issues.length > 0 && !locked && (
        <div className="ai-notice" role="status">
          <strong>识别时的提示</strong>
          <ul>{issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul>
          <small>可直接修改下方字段；提交时按修改后的内容重新校验。</small>
        </div>
      )}
      {locked && (
        <p className="ai-notice" role="status">
          本次内容已锁定。若网络中断，请使用下方按钮重试同一笔，避免重新记账。
        </p>
      )}
      <form className="ai-review-form" onSubmit={submit}>
        <fieldset disabled={busy || locked || disabled}>
          <div className="type-tabs" role="group" aria-label="收支类型">
            {(['支出', '收入'] as const).map((type) => (
              <button type="button" key={type} aria-pressed={draft.money_type === type}
                className={draft.money_type === type ? 'selected' : ''}
                onClick={() => changeType(type)}>{type}</button>
            ))}
          </div>
          {!draft.money_type && <p className="form-error">请选择收入或支出</p>}
          <div className="amount-input">
            <label htmlFor="ai-money">金额</label>
            <div><span>¥</span><input id="ai-money" inputMode="decimal" type="text"
              required maxLength={10} placeholder="待补充"
              value={draft.money} onChange={(e) => field('money', e.currentTarget.value)} /></div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="ai-account">账户</label>
              <select id="ai-account" required value={draft.account_id || ''}
                onChange={(e) => field('account_id', Number(e.currentTarget.value))}>
                <option value="">请选择账户</option>
                {catalog.accounts.map((item) =>
                  <option key={item.id} value={item.id}>{item.name_accounts}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="ai-category">分类</label>
              <select id="ai-category" required value={draft.category_id || ''}
                onChange={(e) => field('category_id', Number(e.currentTarget.value))}>
                <option value="">{draft.money_type ? '请选择分类' : '先选收支类型'}</option>
                {catalog.categories.filter((item) => item.money_type === draft.money_type)
                  .map((item) => <option key={item.id} value={item.id}>{item.name_categories}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label htmlFor="ai-date">日期</label>
            <input id="ai-date" type="date" min="0001-01-01" max="9999-12-31" required
              value={draft.transaction_date}
              onChange={(e) => field('transaction_date', e.currentTarget.value)} />
          </div>
          <div className="field">
            <label htmlFor="ai-description">备注 · 选填</label>
            <input id="ai-description" maxLength={250} value={draft.description ?? ''}
              placeholder="留下一点生活的细节"
              onChange={(e) => field('description', e.currentTarget.value)} />
          </div>
        </fieldset>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="ai-card-actions">
          {!locked && <button type="button" className="secondary" disabled={busy}
            onClick={onDiscard}>放弃草稿</button>}
          <button className="primary" type="submit" disabled={busy || (!locked && disabled)}>
            <Icon name="logo" />
            {busy ? '正在入账…' : locked ? '重试同一笔提交' : '确认入账'}
          </button>
        </div>
      </form>
    </section>
  )
}