import { useState } from 'react'
import { refreshResources } from '../query'
import { useSearchParams } from 'react-router'
import { filters, moveMonth } from '../filters'
import Overview from '../components/Overview'
import AccountReport from '../components/AccountReport'
import TransactionDialog from '../components/TransactionDialog'
import TransactionList from '../components/TransactionList'
import { labels, type Page } from '../workspace'
import type { Account, Category, Transaction } from '../types'
import { useResource } from '../useResource'
import EntityCards from '../components/EntityCards'
import EntityDialog, { type EntityEditor } from '../components/EntityDialog'
export default function LedgerPage({ page }: { page: Page }) {
  const [search, setSearch] = useSearchParams()
  const selected = filters(search)
  function setMonth(month: string) {
    const next = new URLSearchParams(search)
    next.set('month', month)
    setSearch(next)
  }
  const [transaction, setTransaction] = useState<Transaction | 'new' | null>(null)
  function refresh() {
    void refreshResources()
    setRevision((value) => value + 1)
  }
  const [editor, setEditor] = useState<EntityEditor | null>(null)
  const [revision, setRevision] = useState(0)
  const accounts = useResource<Account[]>('/accounts')
  const expense = useResource<Category[]>(
    '/categories?money_type=' + encodeURIComponent('支出'),
  )
  const income = useResource<Category[]>(
    '/categories?money_type=' + encodeURIComponent('收入'),
  )
  const error = accounts.error || expense.error || income.error
  const loading = accounts.loading || expense.loading || income.loading
  const catalog = {
    accounts: accounts.data ?? [],
    categories: [...(expense.data ?? []), ...(income.data ?? [])],
  }
  return (
    <>
      <section className="welcome">
        <div>
          <div className="eyebrow">A LITTLE CLARITY, EVERY DAY</div>
          <h1>{page === 'overview' ? '把日子，记得清楚。' : labels[page]}</h1>
          <p className="subtitle">收入、支出与生活的细节，都在这里。</p>
        </div>
        <div className="welcome-actions">
          <div className="month-picker">
            <button
              aria-label="上个月"
              onClick={() => setMonth(moveMonth(selected.month, -1))}
            >
              ‹
            </button>
            <input
              aria-label="选择月份"
              type="month"
              min="0001-01"
              max="9999-12"
              value={selected.month}
              onChange={(e) => {
                if (e.currentTarget.value) setMonth(e.currentTarget.value)
              }}
            />
            <button
              aria-label="下个月"
              onClick={() => setMonth(moveMonth(selected.month, 1))}
            >
              ›
            </button>
          </div>
          {(page === 'accounts' || page === 'categories') && (
            <button
              className="primary"
              disabled={loading || Boolean(error)}
              onClick={() =>
                setEditor({ kind: page === 'accounts' ? 'account' : 'category' })
              }
            >
              {page === 'accounts' ? '新增账户' : '新增分类'}
            </button>
          )}
          {(page === 'overview' || page === 'transactions') && (
            <button
              className="primary"
              disabled={loading || Boolean(error)}
              onClick={() => setTransaction('new')}
            >
              记一笔
            </button>
          )}
        </div>
      </section>
      <button className="text-button" onClick={() => refresh()}>
        刷新数据
      </button>
      {loading ? (
        <p className="status">正在读取资料…</p>
      ) : error ? (
        <div className="status" role="alert">
          {error.message}
          <button onClick={() => refresh()}>重试</button>
        </div>
      ) : page === 'accounts' ? (
        <AccountReport
          catalog={catalog}
          month={selected.month}
          onEdit={(value) => setEditor({ kind: 'account', value })}
        />
      ) : page === 'categories' ? (
        <EntityCards
          {...catalog}
          kind="category"
          onEdit={(value) => setEditor({ kind: 'category', value })}
        />
      ) : (
        <>
          {page === 'overview' && <Overview month={selected.month} />}
          <TransactionList
            key={JSON.stringify(selected) + revision + page}
            catalog={catalog}
            overview={page === 'overview'}
            onEdit={setTransaction}
          />
        </>
      )}
      {transaction && (
        <TransactionDialog
          key={transaction === 'new' ? 'new' : transaction.id}
          value={transaction === 'new' ? undefined : transaction}
          {...catalog}
          onClose={() => setTransaction(null)}
          onSaved={() => {
            setTransaction(null)
            refresh()
          }}
        />
      )}
      {editor && (
        <EntityDialog
          key={editor.kind + (editor.value?.id ?? 'new')}
          {...editor}
          onClose={() => setEditor(null)}
          onSaved={() => {
            setEditor(null)
            refresh()
          }}
        />
      )}
    </>
  )
}
