import type { Catalog, Account, Category } from '../types'
import Icon from './Icon'
type Props = Catalog & {
  kind: 'account' | 'category'
  onEdit?: (value: Account | Category) => void
}
export default function EntityCards({ accounts, categories, kind, onEdit }: Props) {
  if (kind === 'account')
    return (
      <div className="management-grid">
        {accounts.length ? (
          accounts.map((account) => (
            <article className="account-card" key={account.id}>
              <div className="account-top">
                <span className="category-icon">
                  <Icon name="wallet" />
                </span>
                {onEdit && (
                  <button
                    className="icon-button"
                    aria-label={'编辑账户' + account.name_accounts}
                    onClick={() => onEdit(account)}
                  >
                    <Icon name="edit" />
                  </button>
                )}
              </div>
              <h2>{account.name_accounts}</h2>
              <p>收付款账户</p>
            </article>
          ))
        ) : (
          <div className="empty">还没有账户，先创建一个收付款账户。</div>
        )}
      </div>
    )
  return (
    <div className="category-sections">
      {(['支出', '收入'] as const).map((type) => (
        <article className="panel" key={type}>
          <div className="panel-head">
            <div>
              <h2>{type}分类</h2>
              <p>{categories.filter((c) => c.money_type === type).length} 个分类</p>
            </div>
          </div>
          <div className="category-list">
            {categories
              .filter((c) => c.money_type === type)
              .map((category) => (
                <div className="category-item" key={category.id}>
                  <span className="category-icon">
                    <Icon name={type === '收入' ? 'down' : 'tag'} />
                  </span>
                  <div className="category-name">
                    <strong>{category.name_categories}</strong>
                  </div>
                  {onEdit && (
                    <button
                      className="icon-button"
                      aria-label={'编辑分类' + category.name_categories}
                      onClick={() => onEdit(category)}
                    >
                      <Icon name="edit" />
                    </button>
                  )}
                </div>
              ))}
            {!categories.some((c) => c.money_type === type) && (
              <div className="empty">还没有分类。</div>
            )}
          </div>
        </article>
      ))}
    </div>
  )
}
