export class ApiError extends Error {
  readonly status: number
  readonly requestId: string | null

  constructor(status: number, message: string, requestId: string | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.requestId = requestId
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function getMessage(data: unknown, fallback: string): string {
  if (!isObject(data)) return fallback
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail)) {
    const messages = data.detail.flatMap((item: unknown) => {
      if (!isObject(item) || typeof item.msg !== 'string') return []
      return [item.msg]
    })
    return messages.join('；') || fallback
  }
  return fallback
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'same-origin',
  })
  const text = await response.text()
  let data: unknown
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = undefined
    }
  }
  const requestId = response.headers.get('X-Request-ID')
  if (!response.ok) {
    throw new ApiError(
      response.status,
      getMessage(data, `请求失败（${response.status}）`),
      requestId,
    )
  }
  if (response.status === 204) return undefined as T
  if (!text || data === undefined) {
    throw new ApiError(response.status, '接口返回内容不符合约定', requestId)
  }
  return data as T
}