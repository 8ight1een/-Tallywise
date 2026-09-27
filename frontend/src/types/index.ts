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
