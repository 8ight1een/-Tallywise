export interface User {
  id: number
  email: string
  nickname: string | null
}

export interface LoginResponse {
  message: string
  user: User
}