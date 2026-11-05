export type MoneyType = '收入' | '支出'
export type User = { id: number; email: string; nickname: string | null }
export type Account = { id: number; name_accounts: string; created_at: string }
export type Category = {
  id: number
  name_categories: string
  money_type: MoneyType
  created_at: string
}
export type TransactionInput = {
  account_id: number
  category_id: number
  money: string
  money_type: MoneyType
  description: string | null
  transaction_date: string
}
export type Transaction = TransactionInput & { id: number; created_at: string }
export type TransactionPage = {
  items: Transaction[]
  next_cursor: string | null
  has_more: boolean
  total: number
  total_pages: number
}
export type Summary = {
  money_in: string
  money_out: string
  money_sum: string
  income_count: number
  expense_count: number
}
export type Daily = {
  transaction_date: string
  money_in: string
  money_out: string
}
export type CategoryExpense = {
  category_id: number
  category_name: string
  amount: string
}
export type AccountSummary = {
  account_id: number
  account_name: string
  money_in: string
  money_out: string
  money_sum: string
}
export type Catalog = { accounts: Account[]; categories: Category[] }
