import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, errorText, request } from '../api'
import { buildTransaction, clearPending, readPending, rememberPending, requestDraft,
  toEditable, type DraftResult, type EditableDraft, type PendingSave } from '../ai'
import { amount } from '../format'
import { refreshResources } from '../query'
import { useResource } from '../useResource'
import type { Account, Category, Transaction } from '../types'
import AiDraftCard from '../components/AiDraftCard'
import TransactionDialog from '../components/TransactionDialog'
import Icon from '../components/Icon'
import '../ai-assistant.css'

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
  const [draft, setDraft] = useState<EditableDraft | null>(() => pending?.payload ?? null)
  const [result, setResult] = useState<DraftResult | null>(null)
  const [text, setText] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [busy, setBusy] = useState<'parse' | 'save' | null>(null)
  const [parseError, setParseError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saved, setSaved] = useState<Transaction | null>(null)
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
    if (lock.current || pending || saved || !catalogReady || !hasOptions) return
    const content = text.trim()
    if (!content || [...content].length > 500) {
      setParseError('请输入 1–500 字的一笔收入或支出')
      return
    }
    lock.current = true
    setBusy('parse')
    setParseError('')
    setSaveError('')
    setNotice('')
    setResult(null)
    setDraft(null)
    setSubmitted(content)
    const aborter = new AbortController()
    controller.current = aborter
    const timer = window.setTimeout(() => aborter.abort(), 60_000)
    try {
      const next = await requestDraft(content, aborter.signal)
      if (!mounted.current) return
      setResult(next)
      if (next.fields.single_transaction) setDraft(toEditable(next))
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
    if (lock.current || !draft || saved) return
    let intent: PendingSave
    try {
      if (!pending && (!catalogReady || !hasOptions)) throw new Error('请先读取有效账户和分类')
      intent = pending ?? { key: crypto.randomUUID(), payload: buildTransaction(draft, catalog) }
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
        setSaved(transaction)
        setPending(null)
        setDraft(null)
        setResult(null)
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

  function reset() {
    if (lock.current || pending) return
    resetForm()
  }

  function resetForm() {
    setDraft(null); setResult(null); setSaved(null); setSubmitted(''); setText('')
    setParseError(''); setSaveError(''); setNotice('')
    input.current?.focus()
  }

  function resolvePending() {
    if (lock.current || !pending) return
    if (!window.confirm('请先核对账本，确认这笔记录是否已入账。结束本次提交只会解除页面锁定，不会删除或新增账单；若已经入账，请勿再次录入。确定已核对并结束吗？')) return
    if (!clearPending(userId)) {
      setSaveError('浏览器无法清除待确认记录，请恢复会话存储后再试。')
      return
    }
    setPending(null)
    resetForm()
    setNotice('已结束本次提交，账本中的记录未作更改。')
  }

  const inputDisabled = Boolean(busy || pending || saved || manual)
  const firstAccount = catalog.accounts[0]?.name_accounts ?? '你的账户'
  const examples = [
    `今天午饭花了 25 元，用${firstAccount}支付`,
    `昨天用${firstAccount}买书花了 48 元`,
    `今天兼职收入 200 元，收到${firstAccount}`,
  ]

  return (
    <div className="ai-page">
      <section className="welcome">
        <div>
          <div className="eyebrow">A LITTLE HELP, EVERY DAY</div>
          <h1>说一句，记一笔。</h1>
          <p className="subtitle">把琐碎的整理交给助手，把最后的确认留给自己。</p>
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
              <div><h2 id="ai-title">AI 助手</h2><p>一句话记账 · 每次一笔</p></div></div>
            <span className="ai-badge">先核对，再入账</span>
          </div>
          <div className="ai-conversation-body">
            <div className="ai-welcome-mark"><Icon name="leaf" /></div>
            <h2>今天，又有了什么小记录？</h2>
            <p>说清什么时候、花了多少、用哪个账户。<br />我来整理，你来确认。</p>
            <div className="ai-examples" aria-label="记账示例">
              {examples.map((example, index) => <button className="ai-example" key={example}
                disabled={inputDisabled} onClick={() => {
                  setText(example); setDraft(null); setResult(null); setSubmitted('')
                  setParseError(''); setSaveError(''); input.current?.focus()
                }}><Icon name={['cup', 'book', 'wallet'][index]} /><span>{example}</span><Icon name="arrow" /></button>)}
            </div>
            {submitted && <div className="ai-user-message"><small>你的描述</small><p>{submitted}</p></div>}
            <div className="ai-feedback" role="status" aria-live="polite">
              {busy === 'parse' ? '正在整理金额、账户和分类…' : saved ? '这一笔已记好。' : pending
                ? '这笔提交的结果需要确认，请在账单卡片中重试。'
                : draft ? '已整理好草稿，请在账单卡片中核对或补全。'
                : result && !result.fields.single_transaction ? '暂时只能处理单笔收入或支出，请重新描述。' : ''}
            </div>
            {result && !result.fields.single_transaction && <div className="ai-notice">
              {result.issues.map((issue, index) => <p key={index}>{issue}</p>)}
              <p>多笔请拆开输入；当前账本也没有专用转账功能，请勿把转账误记为收入或支出。</p>
            </div>}
            {parseError && <p className="ai-error" role="alert">{parseError}</p>}
          </div>
          <form className="ai-composer" onSubmit={parse}>
            <label htmlFor="ai-text">描述一笔收支</label>
            <textarea ref={input} id="ai-text" rows={3} maxLength={500} required
              disabled={inputDisabled} value={text} aria-describedby="ai-input-hint"
              placeholder="例如：今天午饭花了 25 元，用微信支付"
              onChange={(e) => {
                setText(e.currentTarget.value); setDraft(null); setResult(null)
                setSubmitted(''); setParseError(''); setSaveError('')
              }} />
            <div className="ai-composer-bottom">
              <span id="ai-input-hint">{text.length}/500 · 生成草稿不会入账</span>
              <button className="primary" disabled={inputDisabled || !catalogReady || !hasOptions || !text.trim()}>
                {busy === 'parse' ? '正在解析…' : parseError ? '重新解析' : '生成草稿'}<Icon name="arrow" />
              </button>
            </div>
          </form>
        </section>

        <div className="ai-review-column">
          {draft ? <AiDraftCard draft={draft} catalog={catalog} issues={result?.issues ?? []}
            busy={busy === 'save'} locked={Boolean(pending)} disabled={!catalogReady || !hasOptions}
            error={saveError} onChange={(next) => { setDraft(next); setSaveError('') }}
            onSave={() => void save()} onDiscard={reset} /> : saved ? (
            <section className="panel ai-success">
              <span className="ai-success-mark"><Icon name="logo" /></span>
              <span className="ai-kicker">A SMALL MOMENT, SAVED</span>
              <h2>这一笔，记好了。</h2>
              <p className="ai-saved-amount">{saved.money_type === '支出' ? '−' : '+'} ¥{amount(saved.money)}</p>
              <p>{saved.description || saved.money_type} · {saved.transaction_date}</p>
              <p className="ai-muted">记录编号 #{saved.id}</p>
              <div className="ai-success-actions">
                <Link className="primary" to={'/transactions?month=' + saved.transaction_date.slice(0, 7)}>查看这月账单</Link>
                <button className="secondary" onClick={reset}>再记一笔</button>
              </div>
              {notice && <p role="status">{notice}</p>}
            </section>
          ) : (
            <section className="panel ai-placeholder">
              <span className="ai-kicker">YOUR NEXT LITTLE RECORD</span>
              <span className="ai-empty-icon"><Icon name="book" /></span>
              <h2>账单，会出现在这里</h2>
              <p>输入一句话，生成可编辑的草稿。<br />确认之前，不会改变你的账本。</p>
              <ol className="ai-steps"><li>说说这笔收支</li><li>核对金额与归属</li><li>确认，收入账本</li></ol>
            </section>
          )}
          <div className="ai-tip"><Icon name="leaf" /><p>信息不完整也没关系。先说出来，再慢慢补齐。</p></div>
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
        setManual(false); reset(); void refreshResources(); setNotice('手动记账已保存，可到收支明细中查看。')
      }} />}
      {!saved && notice && <p className="ai-notice" role="status">{notice}</p>}
    </div>
  )
}
