import { localDate } from './format'
export function validMonth(value: string | null) {
  return value && /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(value)
    ? value
    : localDate().slice(0, 7)
}
export function moveMonth(value: string, delta: number) {
  const [year, month] = value.split('-').map(Number)
  const index = (year - 1) * 12 + month - 1 + delta
  if (index < 0 || index >= 9999 * 12) return value
  return (
    String(Math.floor(index / 12) + 1).padStart(4, '0') +
    '-' +
    String((index % 12) + 1).padStart(2, '0')
  )
}
export function filters(search: URLSearchParams) {
  const type = search.get('money_type') ?? ''
  const id = search.get('account_id') ?? ''
  return {
    month: validMonth(search.get('month')),
    q: (search.get('q') ?? '').slice(0, 250),
    money_type: type === '收入' || type === '支出' ? type : '',
    account_id: /^[1-9]\d*$/.test(id) && Number(id) <= 2147483647 ? id : '',
  }
}
