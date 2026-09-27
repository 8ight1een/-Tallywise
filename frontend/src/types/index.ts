export interface User {
  id: number
  email: string
  nickname: string | null
}

export interface LoginResponse {
  message: string
  user: User
}

export interface Summary {
  money_in: number
  money_out: number
  money_sum: number
}

export type MoneyType = '收入' | '支出'

export type MonthSelection = 'current' | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12

export interface Category {
  id: number
  name_categories: string
}

export interface Transaction {
  id: number
  account_id: number
  category_id: number
  money: number | string
  money_type: MoneyType
  description: string | null
  transaction_date: string
}
