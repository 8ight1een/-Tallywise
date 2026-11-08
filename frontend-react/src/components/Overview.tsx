import type { Summary, Daily, CategoryExpense } from '../types'
import { useResource } from '../useResource'
import { amount } from '../format'
import Icon from './Icon'
import Charts from './Charts'
export default function Overview({ month }: { month: string }) {
  const query = '?year=' + month.slice(0, 4) + '&month=' + Number(month.slice(5))
  const summary = useResource<Summary>('/summary' + query)
  const daily = useResource<Daily[]>('/reports/daily-trend' + query)
  const categories = useResource<CategoryExpense[]>(
    '/reports/category-expenses' + query,
  )
  const error = summary.error || daily.error || categories.error
  if (error)
    return (
      <p className="status" role="alert">
        {error.message}，请用页面的刷新按钮重试。
      </p>
    )
  if (summary.loading || daily.loading || categories.loading || !summary.data)
    return <p className="status">正在读取月度统计…</p>
  const data = summary.data
  const cards = [
    {
      title: '本月结余',
      value: data.money_sum,
      icon: 'wallet',
      note: '本月收入 − 本月支出',
    },
    {
      title: '本月收入',
      value: data.money_in,
      icon: 'down',
      note: data.income_count + ' 笔收入',
    },
    {
      title: '本月支出',
      value: data.money_out,
      icon: 'up',
      note: data.expense_count + ' 笔支出',
    },
  ]
  return (
    <>
      <div className="stats">
        {cards.map((card, index) => (
          <article
            className={'stat ' + (index === 0 ? 'featured' : '')}
            key={card.title}
          >
            <div className="stat-head">
              {card.title}
              <span className="stat-icon">
                <Icon name={card.icon} />
              </span>
            </div>
            <div className="amount">
              <span className="currency">¥</span>
              {amount(card.value)}
            </div>
            <div className="stat-foot">{card.note}</div>
          </article>
        ))}
      </div>
      <Charts
        month={month}
        daily={daily.data ?? []}
        categories={categories.data ?? []}
      />
    </>
  )
}
