import { ApiError, request as send } from './api/http'
export { ApiError }

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  try {
    return await send<T>('/api' + path, { ...options, headers })
  } catch (error) {
    if (error instanceof ApiError && error.status === 401 && !path.startsWith('/auth/')) {
      window.dispatchEvent(new Event('session-expired'))
    }
    throw error
  }
}

export function errorText(error: unknown) {
  return error instanceof Error ? error.message : '请求失败，请重试'
}

export function json(method: 'POST' | 'PUT' | 'DELETE', data?: unknown): RequestInit {
  return { method, body: data === undefined ? undefined : JSON.stringify(data) }
}
