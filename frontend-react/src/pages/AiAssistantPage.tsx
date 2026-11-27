import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, errorText, request } from '../api'
import { buildTransaction, clearPending, readPending, rememberPending, requestDrafts,
  toEditable, type EditableDraft, type PendingSave } from '../ai'
import { amount } from '../format'
import { refreshResources } from '../query'
import { useResource } from '../useResource'
import type { Account, Category, Transaction } from '../types'
import AiDraftCard from '../components/AiDraftCard'
import TransactionDialog from '../components/TransactionDialog'
import Icon from '../components/Icon'
import '../ai-assistant.css'

type DraftRow = { id: number; draft: EditableDraft; issues: string[] }
const textLimit = 1500

export default function AiAssistantPage({ userId }: { userId: number }) {
  const accounts = useResource<Account[]>('/accounts')
  const expense = useResource<Category[]>('/categories?money_type=' + encodeURIComponent('支出'))
  const income = useResource<Category[]>('/categories?money_type=' + encodeURIComponent('收入'))
  const catalog = { accounts: accounts.data ?? [],
    categories: [...(expense.data ?? []), ...(income.data ?? [])] }
  const catalogError = accounts.error || expense.error || income.error
  const catalogReady = Boolean(accounts.data && expense.data && income.data) && !catalogError
  const hasOptions = catalog.accounts.length > 0 && catalog.categories.length > 0
  const [pending, setPending] = useState<PendingSave | null>(() => readPending(userId))
  const [rows, setRows] = useState<DraftRow[]>(() =>
    pending ? [{ id: 0, draft: pending.payload, issues: [] }] : [])
  const [selectedId, setSelectedId] = useState(0)
  const selected = rows.find(row => row.id === selectedId) ?? rows[0]
  const [warnings, setWarnings] = useState<string[]>([])
  const [text, setText] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [busy, setBusy] = useState<'parse' | 'save' | null>(null)
  const [parseError, setParseError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saved, setSaved] = useState<Transaction[]>([])
  const [notice, setNotice] = useState('')
  const [manual, setManual] = useState(false)
  const lock = useRef(false)
  const controller = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  const input = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; controller.current?.abort() }
  }, [])

  async function parse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (lock.current || pending || rows.length || saved.length || !catalogReady || !hasOptions) return
    const content = text.trim()
    if (!content || [...content].length > textLimit) {
      setParseError(`请输入 1–${textLimit} 字的收支描述`)
      return
    }
    lock.current = true
    setBusy('parse')
    setParseError('')
    setSaveError('')
    setNotice('')
    setWarnings([])
    setSubmitted(content)
    const aborter = new AbortController()
    controller.current = aborter
    const timer = window.setTimeout(() => aborter.abort(), 125_000)
    try {
      const next = await requestDrafts(content, aborter.signal)
      if (!mounted.current) return
      setRows(next.drafts.map((item, id) => ({ id, draft: toEditable(item), issues: item.issues })))
      setSelectedId(0)
      setWarnings(next.warnings)
      if (!next.drafts.length) setNotice('没有识别到可记账的收支，可以修改描述再试。')
    } catch (error) {
      if (mounted.current) setParseError(aborter.signal.aborted
        ? '解析等待超时，尚未入账。可以重新解析或改为手动记账。' : errorText(error))
    } finally {
      window.clearTimeout(timer)
      controller.current = null
      lock.current = false
      if (mounted.current) setBusy(null)
    }
  }

  async function save() {
    if (lock.current || !selected) return
    let intent: PendingSave
    try {
      if (!pending && (!catalogReady || !hasOptions)) throw new Error('请先读取有效账户和分类')
      intent = pending ?? { key: crypto.randomUUID(), payload: buildTransaction(selected.draft, catalog) }
      try { rememberPending(userId, intent) }
      catch { throw new Error('浏览器无法暂存本次提交，请允许会话存储后再试。尚未发送入账请求。') }
    } catch (error) { setSaveError(errorText(error)); return }
    lock.current = true
    setPending(intent)
    setBusy('save')
    setSaveError('')
    const aborter = new AbortController()
    controller.current = aborter
    const timer = window.setTimeout(() => aborter.abort(), 20_000)
    try {
      const transaction = await request<Transaction>('/transactions', {
        method: 'POST', body: JSON.stringify(intent.payload),
        headers: { 'Idempotency-Key': intent.key }, signal: aborter.signal,
      })
      clearPending(userId)
      void refreshResources(true).catch(() => {
        if (mounted.current) setNotice('已入账，数据刷新失败，请在账本页点击“刷新数据”。')
      })
      if (mounted.current) {
        setSaved(previous => [...previous, transaction])
        setPending(null)
        setRows(previous => previous.filter(row => row.id !== selected.id))
      }
    } catch (error) {
      const rejected = error instanceof ApiError && [400, 403, 404, 422, 429].includes(error.status)
      const cleared = rejected && clearPending(userId)
      if (mounted.current) {
        if (cleared) setPending(null)
        setSaveError(cleared ? errorText(error)
          : '暂时无法确认入账结果。请重试同一笔提交，系统会复用原编号，避免重复入账。')
      }
    } finally {
      window.clearTimeout(timer)
      controller.current = null
      lock.current = false
      if (mounted.current) setBusy(null)
    }
  }

  function editDraft(draft: EditableDraft) {
    if (!selected || pending || lock.current) return
    const issues: string[] = []
    try { buildTransaction(draft, catalog) }
    catch (error) { issues.push(errorText(error)) }
    setRows(rows.map(row => row.id === selected.id ? { ...row, draft, issues } : row))
    setSaveError('')
  }

  function resetForm() {
    setRows([]); setWarnings([]); setSaved([]); setSubmitted(''); setText('')
    setParseError(''); setSaveError(''); setNotice('')
    input.current?.focus()
  }

  function removeSelected() {
    if (!selected) return
    if (rows.length === 1 && !saved.length) resetForm()
    else setRows(rows.filter(row => row.id !== selected.id))
    setSaveError('')
  }

  function resolvePending() {
    if (lock.current || !pending) return
    if (!window.confirm('请先核对账本，确认这笔记录是否已入账。结束本次提交只会解除页面锁定，不会删除或新增账单；若已经入账，请勿再次录入。确定已核对并结束吗？')) return
    if (!clearPending(userId)) {
      setSaveError('浏览器无法清除待确认记录，请恢复会话存储后再试。')
      return
    }
    setPending(null)
    removeSelected()
    setNotice('已结束本次提交，账本中的记录未作更改。')
  }

  const inputDisabled = Boolean(busy || pending || rows.length || saved.length || manual)
  const needsInput = rows.filter(row => row.issues.length > 0).length
  const lastSaved = saved[saved.length - 1]
  const firstAccount = catalog.accounts[0]?.name_accounts ?? '你的账户'
  const examples = [
    `今天用${firstAccount}付了早餐 8 元、午饭 18 元，两顿合计 26 元`,
    `昨天用${firstAccount}买书花了 48 元`,
    `今天兼职收入 200 元，收到${firstAccount}`,
  ]

  return (
    <div className="ai-page">
      <section className="welcome">
        <div>
          <div className="eyebrow">A LITTLE HELP, EVERY DAY</div>
          <h1>一段话，记多笔。</h1>
          <p className="subtitle">一起写下几笔收支，生成草稿后逐笔核对。</p>
        </div>
        <button className="secondary" disabled={!catalogReady || !hasOptions || inputDisabled}
          onClick={() => setManual(true)}><Icon name="edit" /> 手动记账</button>
      </section>

      {!catalogReady && <div className="ai-notice" role={catalogError ? 'alert' : 'status'}>
        {catalogError ? catalogError.message : '正在读取你的账户和分类…'}
        {catalogError && <button className="text-button" onClick={() => void refreshResources()}>重新读取</button>}
      </div>}
      {catalogReady && !hasOptions && <div className="ai-notice" role="status">
        先创建至少一个账户和一个分类，再开始记账。<Link to="/accounts">管理账户</Link> · <Link to="/categories">管理分类</Link>
      </div>}

      <div className="ai-layout">
        <section className="panel ai-conversation" aria-labelledby="ai-title">
          <div className="ai-conversation-head">
            <div className="ai-heading-row"><span className="ai-avatar"><Icon name="leaf" /></span>
              <div><h2 id="ai-title">AI 助手</h2><p>每次最多识别 10 笔收支</p></div></div>
            <span className="ai-badge">先核对，再入账</span>
          </div>
          <div className="ai-conversation-body">
            <div className="ai-welcome-mark"><Icon name="leaf" /></div>
            <h2>今天，又有了什么小记录？</h2>
            <p>说清什么时候、花了多少、用哪个账户。<br />我来整理，你来确认。</p>
            <div className="ai-examples" aria-label="记账示例">
              {examples.map((example, index) => <button className="ai-example" key={example}
                disabled={inputDisabled} onClick={() => {
                  setText(example); setWarnings([]); setSubmitted('')
                  setParseError(''); setNotice(''); input.current?.focus()
                }}><Icon name={['cup', 'book', 'wallet'][index]} /><span>{example}</span><Icon name="arrow" /></button>)}
            </div>
            {submitted && <div className="ai-user-message"><small>你的描述</small><p>{submitted}</p></div>}
            <div className="ai-feedback" role="status" aria-live="polite">
              {busy === 'parse' && '正在整理金额、账户和分类…'}
              {pending && !busy && '这笔提交的结果需要确认，请在账单卡片中重试。'}
              {notice}
            </div>
            {warnings.length > 0 && <div className="ai-notice">
              {warnings.map((warning, index) => <p key={index}>{warning}</p>)}
            </div>}
            {parseError && <p className="ai-error" role="alert">{parseError}</p>}
          </div>
          <form className="ai-composer" onSubmit={parse}>
            <label htmlFor="ai-text">描述你的收支</label>
            <textarea ref={input} id="ai-text" rows={4} required
              disabled={inputDisabled} value={text} aria-describedby="ai-input-hint"
              placeholder="例如：昨天微信付午饭 25 元，今天坐地铁花了 4 元。"
              onChange={(e) => {
                setText(e.currentTarget.value); setWarnings([]); setNotice('')
                setSubmitted(''); setParseError('')
              }} />
            <div className="ai-composer-bottom">
              <span id="ai-input-hint">{[...text].length}/{textLimit} 字 · 每段最多 10 笔</span>
              <button className="primary" disabled={inputDisabled || !catalogReady || !hasOptions || !text.trim()}>
                {busy === 'parse' ? '正在解析…' : parseError ? '重新解析' : '生成草稿'}<Icon name="arrow" />
              </button>
            </div>
          </form>
        </section>

        <div className="ai-review-column">
          {selected && <section className="panel ai-draft-list" aria-label="草稿列表">
            <h2>待核对草稿</h2>
            <p role="status">{pending
              ? `1 笔等待确认提交结果 · 另有 ${rows.length - 1} 笔草稿`
              : `${rows.length - needsInput} 笔可确认 · ${needsInput} 笔待补充`} · {saved.length} 笔已入账</p>
            {rows.map(row => (
              <button key={row.id} type="button" className="ai-draft-row"
                aria-pressed={row.id === selected.id} disabled={Boolean(busy || pending)}
                onClick={() => { setSelectedId(row.id); setSaveError('') }}>
                <span>{row.draft.description || `第 ${row.id + 1} 笔收支`}</span>
                <strong>{row.draft.money ? `¥${row.draft.money}` : '金额待填'}</strong>
                <small>{pending && row.id === selected.id ? '等待确认' : row.issues.length ? '待补充' : '可确认'}</small>
              </button>
            ))}
          </section>}
          {selected ? <AiDraftCard draft={selected.draft} catalog={catalog} issues={selected.issues}
            busy={busy === 'save'} locked={Boolean(pending)} disabled={!catalogReady || !hasOptions}
            error={saveError} onChange={editDraft}
            onSave={() => void save()} onDiscard={removeSelected} /> : lastSaved ? (
            <section className="panel ai-success">
              <span className="ai-success-mark"><Icon name="logo" /></span>
              <span className="ai-kicker">A SMALL MOMENT, SAVED</span>
              <h2>{saved.length === 1 ? '这一笔，记好了。' : `${saved.length} 笔收支已入账`}</h2>
              {saved.map(item => <p key={item.id}>{item.description || item.money_type}
                {' · '}{item.money_type === '支出' ? '−' : '+'}¥{amount(item.money)} · {item.transaction_date}</p>)}
              <div className="ai-success-actions">
                <Link className="primary" to={'/transactions?month=' + lastSaved.transaction_date.slice(0, 7)}>查看最近入账月份</Link>
                <button className="secondary" onClick={resetForm}>继续记账</button>
              </div>
            </section>
          ) : (
            <section className="panel ai-placeholder">
              <span className="ai-kicker">YOUR NEXT LITTLE RECORD</span>
              <span className="ai-empty-icon"><Icon name="book" /></span>
              <h2>账单，会出现在这里</h2>
              <p>可以把一天的收支写在一起，每笔都能单独修改。</p>
              <ol className="ai-steps"><li>描述收支</li><li>选择草稿，核对金额与账户</li><li>逐笔确认入账</li></ol>
            </section>
          )}
          {selected && <div className="ai-tip"><Icon name="leaf" /><p>切换草稿会保留修改。请在离开页面前处理完未提交的草稿。</p></div>}
          {pending && <div className="ai-pending-actions">
            <Link className="text-button" target="_blank" rel="noopener noreferrer"
              to={'/transactions?month=' + pending.payload.transaction_date.slice(0, 7)}>在新标签页核对账本</Link>
            <button className="text-button" disabled={Boolean(busy)} onClick={resolvePending}>
              已核对账本，结束本次提交
            </button>
          </div>}
        </div>
      </div>
      {manual && <TransactionDialog {...catalog} onClose={() => setManual(false)} onSaved={() => {
        setManual(false); resetForm(); void refreshResources(); setNotice('手动记账已保存，可到收支明细中查看。')
      }} />}
    </div>
  )
}
