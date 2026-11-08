import { useState } from 'react'
import { refreshResources } from '../query'
import { useSearchParams } from 'react-router'
import type { Catalog, Transaction, TransactionPage } from '../types'
import { useResource } from '../useResource'
import { filters } from '../filters'
import TransactionTable from './TransactionTable'
import Icon from './Icon'
type Props = {
  catalog: Catalog
  overview?: boolean
  onEdit: (row: Transaction) => void
}
export default function TransactionList({
  catalog,
  overview = false,
  onEdit,
}: Props) {
  const [search, setSearch] = useSearchParams()
  const selected = filters(search)
  const [query, setQuery] = useState(selected.q)
  const [history, setHistory] = useState<(string | null)[]>([null])
  const [index, setIndex] = useState(0)
  const params = new URLSearchParams({
    year: selected.month.slice(0, 4),
    month: String(Number(selected.month.slice(5))),
    limit: overview ? '5' : '20',
  })
  if (!overview)
    for (const key of ['q', 'money_type', 'account_id'] as const) {
      if (selected[key]) params.set(key, selected[key])
    }
  const cursor = history[index]
  if (cursor) params.set('cursor', cursor)
  const result = useResource<TransactionPage>('/transactions/page?' + params)
  function change(key: string, value: string) {
    const next = new URLSearchParams(search)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearch(next)
  }
  function nextPage() {
    const next = result.data?.next_cursor
    if (!next || result.loading) return
    setHistory((previous) => [...previous.slice(0, index + 1), next])
    setIndex((previous) => previous + 1)
  }
  return (
    <section className="panel ledger">
      <div className="panel-head">
        <div>
          <h2>{overview ? '最近收支' : '全部收支'}</h2>
          <p>按月份查看，记录生活的细节。</p>
        </div>
      </div>
      {!overview && (
        <div className="toolbar">
          <form
            className="search-box"
            onSubmit={(event) => {
              event.preventDefault()
              change('q', query.trim())
            }}
          >
            <Icon name="search" />
            <input
              aria-label="搜索备注、账户或分类"
              placeholder="搜索备注、账户或分类"
              maxLength={250}
              value={query}
              onChange={(e) => setQuery(e.currentTarget.value)}
            />
            <button type="submit">搜索</button>
          </form>
          <select
            className="filter-select"
            aria-label="筛选收支类型"
            value={selected.money_type}
            onChange={(e) => change('money_type', e.currentTarget.value)}
          >
            <option value="">全部收支</option>
            <option>支出</option>
            <option>收入</option>
          </select>
          <select
            className="filter-select"
            aria-label="筛选账户"
            value={selected.account_id}
            onChange={(e) => change('account_id', e.currentTarget.value)}
          >
            <option value="">全部账户</option>
            {catalog.accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name_accounts}
              </option>
            ))}
          </select>
        </div>
      )}
      {result.loading ? (
        <p className="status">正在读取流水…</p>
      ) : result.error ? (
        <div className="status" role="alert">
          {result.error.message}
          <button onClick={() => void refreshResources()}>重试</button>
        </div>
      ) : (
        <TransactionTable
          rows={result.data?.items ?? []}
          {...catalog}
          onEdit={onEdit}
        />
      )}
      <div className="table-footer">
        <span>共 {result.data?.total ?? '…'} 笔记录</span>
        {!overview && (
          <div className="paging">
            <button
              disabled={index === 0 || result.loading}
              onClick={() => setIndex((v) => v - 1)}
              aria-label="上一页"
            >
              ‹
            </button>
            <span>
              {result.data?.total === 0 ? 0 : index + 1} /{' '}
              {result.data?.total_pages ?? '…'}
            </span>
            <button
              disabled={
                result.loading || !result.data?.has_more || Boolean(result.error)
              }
              onClick={nextPage}
              aria-label="下一页"
            >
              ›
            </button>
          </div>
        )}
      </div>
    </section>
  )
}
