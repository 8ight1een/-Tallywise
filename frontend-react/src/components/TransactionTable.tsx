import type { Catalog, Transaction } from '../types'
import { amount } from '../format'
import Icon from './Icon'
type Props = Catalog & { rows: Transaction[]; onEdit?: (row: Transaction) => void }
export default function TransactionTable({
  rows,
  accounts,
  categories,
  onEdit,
}: Props) {
  if (!rows.length)
    return (
      <div className="empty">
        <strong>这里还没有记录</strong>
        <span>调整筛选条件，或者记下第一笔。</span>
      </div>
    )
  return (
    <div className="table-wrap">
      <table>
        <colgroup>
          {['32%', '15%', '16%', '15%', '15%', '7%'].map((width, index) => (
            <col key={index} style={{ width }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {['收支事项', '分类', '账户', '日期', '金额', '操作'].map((text) => (
              <th key={text}>{text}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>
                <div className="description-cell">
                  <span
                    className={
                      'category-icon ' + (row.money_type === '收入' ? 'income' : '')
                    }
                  >
                    <Icon name={row.money_type === '收入' ? 'down' : 'tag'} />
                  </span>
                  <span className="record-text">
                    <strong>{row.description || '未填写备注'}</strong>
                    <small>{row.money_type}</small>
                  </span>
                </div>
              </td>
              <td>
                <span className="tag">
                  {categories.find((c) => c.id === row.category_id)
                    ?.name_categories ?? '未知分类'}
                </span>
              </td>
              <td>
                <span className="tag">
                  {accounts.find((a) => a.id === row.account_id)?.name_accounts ??
                    '未知账户'}
                </span>
              </td>
              <td className="date-cell">
                {row.transaction_date.slice(5).replace('-', '.')}
              </td>
              <td
                className={
                  'money-cell ' + (row.money_type === '收入' ? 'income' : '')
                }
              >
                {row.money_type === '收入' ? '+' : '−'} {amount(row.money)}
              </td>
              <td className="row-action">
                {onEdit && (
                  <button
                    className="icon-button"
                    aria-label={'编辑' + (row.description || '记录')}
                    onClick={() => onEdit(row)}
                  >
                    <Icon name="edit" />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
