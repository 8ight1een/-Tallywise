import { useState, type CSSProperties } from 'react'
import type { CategoryExpense, Daily, MoneyType } from '../types'
import { amount } from '../format'
import Icon from './Icon'
export default function Charts({
  daily,
  categories,
  month,
}: {
  daily: Daily[]
  categories: CategoryExpense[]
  month: string
}) {
  const [type, setType] = useState<MoneyType>('支出')
  const values = [...daily]
    .sort((a, b) => a.transaction_date.localeCompare(b.transaction_date))
    .map((row) => Number(type === '收入' ? row.money_in : row.money_out))
  const top = Math.max(1, ...values)
  const x = (index: number) => 45 + (index * 519) / Math.max(1, values.length - 1)
  const y = (value: number) => 147 - (value / top) * 119
  const points = values.map((value, index) => x(index) + ',' + y(value)).join(' ')
  const total = categories.reduce((sum, item) => sum + Number(item.amount), 0)
  const colors = ['#537c55', '#91aa6e', '#bfd092', '#dbe4bd', '#e8eddc']
  const sorted = [...categories].sort((a, b) => Number(b.amount) - Number(a.amount))
  const groups =
    sorted.length > 5
      ? [
          ...sorted.slice(0, 4),
          {
            category_id: -1,
            category_name: '其他分类',
            amount: String(
              sorted.slice(4).reduce((sum, row) => sum + Number(row.amount), 0),
            ),
          },
        ]
      : sorted
  let start = 0
  const stops = groups.map((group, index) => {
    const from = start
    start += total ? (Number(group.amount) / total) * 100 : 0
    return colors[index] + ' ' + from + '% ' + start + '%'
  })
  const donutStyle: CSSProperties = {
    background: total ? 'conic-gradient(' + stops.join(',') + ')' : '#edf1e7',
  }
  return (
    <div className="analytics">
      <article className="panel">
        <div className="panel-head">
          <div>
            <h2>收支趋势</h2>
            <p>
              {month} · 每日{type}
            </p>
          </div>
          <div className="segmented">
            {(['支出', '收入'] as const).map((item) => (
              <button
                key={item}
                className={type === item ? 'selected' : ''}
                aria-pressed={type === item}
                onClick={() => setType(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
        <div className="chart-number">
          <strong>¥ {amount(values.reduce((sum, value) => sum + value, 0))}</strong>
          <span>本月累计{type}</span>
        </div>
        <div className="chart-wrap">
          <svg
            className="chart"
            viewBox="0 0 580 190"
            role="img"
            aria-label={month + '每日' + type}
          >
            {[0, 1, 2, 3].map((index) => (
              <g key={index}>
                <line
                  className="grid"
                  x1="45"
                  x2="564"
                  y1={y((top * index) / 3)}
                  y2={y((top * index) / 3)}
                />
                <text x="33" y={y((top * index) / 3) + 3} textAnchor="end">
                  {Math.round((top * index) / 3)}
                </text>
              </g>
            ))}
            <polygon
              points={
                '45,147 ' +
                points +
                ' ' +
                x(Math.max(0, values.length - 1)) +
                ',147'
              }
              fill="#adc78e"
              opacity=".2"
            />
            <polyline className="trend-line" points={points} />
            {values.map((value, index) => (
              <circle
                key={index}
                cx={x(index)}
                cy={y(value)}
                r="5"
                fill="transparent"
              >
                <title>
                  {index + 1}日 ¥{amount(value)}
                </title>
              </circle>
            ))}
            {[1, 7, 14, 21, values.length]
              .filter((day) => day > 0 && day <= values.length)
              .map((day, index) => (
                <text key={index} x={x(day - 1)} y="176" textAnchor="middle">
                  {month.slice(5)}/{String(day).padStart(2, '0')}
                </text>
              ))}
          </svg>
        </div>
      </article>
      <article className="panel">
        <div className="panel-head">
          <div>
            <h2>钱花在哪里</h2>
            <p>本月支出 · 按分类</p>
          </div>
          <Icon name="tag" />
        </div>
        <div className="donut-layout">
          <div
            className="donut"
            style={donutStyle}
            role="img"
            aria-label={
              total
                ? groups
                    .map(
                      (g) =>
                        g.category_name +
                        ' ' +
                        ((Number(g.amount) / total) * 100).toFixed(1) +
                        '%',
                    )
                    .join('，')
                : '本月暂无支出'
            }
          >
            <div className="donut-label">
              <strong>{categories.length}</strong>
              <span>支出分类</span>
            </div>
          </div>
          <div className="legend">
            {groups.map((group, index) => (
              <div className="legend-row" key={group.category_id}>
                <i style={{ background: colors[index] }} />
                <span title={group.category_name}>{group.category_name}</span>
                <b>
                  {total
                    ? ((Number(group.amount) / total) * 100).toFixed(1)
                    : '0.0'}
                  %
                </b>
              </div>
            ))}
            {!groups.length && <span>还没有支出记录</span>}
          </div>
        </div>
        <div className="insight">
          <Icon name="leaf" />
          <span>
            {total && groups[0]
              ? groups[0].category_name +
                '占支出的 ' +
                ((Number(groups[0].amount) / total) * 100).toFixed(1) +
                '%，是本月最大的一项。'
              : '从第一笔记录开始，了解自己的消费习惯。'}
          </span>
        </div>
      </article>
    </div>
  )
}
