import type { AccountSummary, Catalog, Account, Category } from '../types'
import { useResource } from '../useResource'
import { amount } from '../format'
import Icon from './Icon'
export default function AccountReport({
  catalog,
  month,
  onEdit,
}: {
  catalog: Catalog
  month: string
  onEdit: (value: Account | Category) => void
}) {
  const result = useResource<AccountSummary[]>(
    '/reports/account-summary?year=' +
      month.slice(0, 4) +
      '&month=' +
      Number(month.slice(5)),
  )
  if (result.loading) return <p className="status">正在读取账户汇总…</p>
  if (result.error) return <p role="alert">{result.error.message}，请刷新重试。</p>
  return (
    <>
      <div className="management-grid">
        {catalog.accounts.map((account) => {
          const summary = result.data?.find((row) => row.account_id === account.id)
          return (
            <article className="account-card" key={account.id}>
              <div className="account-top">
                <span className="category-icon">
                  <Icon name="wallet" />
                </span>
                <button
                  className="icon-button"
                  aria-label={'编辑账户' + account.name_accounts}
                  onClick={() => onEdit(account)}
                >
                  <Icon name="edit" />
                </button>
              </div>
              <h2>{account.name_accounts}</h2>
              <p>所选月份收支</p>
              <div className="account-values">
                <div>
                  <small>本月收入</small>
                  <strong>¥ {summary ? amount(summary.money_in) : '—'}</strong>
                </div>
                <div>
                  <small>本月支出</small>
                  <strong>¥ {summary ? amount(summary.money_out) : '—'}</strong>
                </div>
              </div>
            </article>
          )
        })}
        {!catalog.accounts.length && <div className="empty">还没有账户。</div>}
      </div>
      <p className="management-note">所选月份的收支不代表账户实际余额。</p>
    </>
  )
}
