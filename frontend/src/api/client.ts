type RequestOptions = Omit<RequestInit,'body'>&{
  json?:unknown
  requireAuth?:boolean
  fallbackMessage?:string
}

class ApiRequestError extends Error{
  status:number
  message:string

  constructor(message:string,status:number){
    super(message)
    this.status = status
    this.message = message
    this.name = 'ApiRequestError'
  }
}

let sessionVersion = 0
let expired = false
let unauthorizedHandler:(()=>void)| undefined

export function resetApiSession() {
  sessionVersion++
  expired = false
}

export function onUnauthorized(handler:()=>void){
  unauthorizedHandler = handler
  return ()=>{
    if(unauthorizedHandler === handler){
      unauthorizedHandler = undefined
    }
}
}

export function isUnauthorized(error: unknown) {
  return error instanceof ApiRequestError && error.status === 401
}

export function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiRequestError ? error.message : fallback
}

function detailMessage(data: unknown, fallback: string): string {
  const detail = (data as { detail?: unknown } | null)?.detail

  if (typeof detail === 'string' && detail) {
    return detail
  }
  return fallback
}


export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { json, requireAuth = true, fallbackMessage = '请求失败,请稍后重试',...init } = options
  const version = sessionVersion
  const headers=new Headers(init.headers)
  if(json !== undefined) headers.set('Content-Type','application/json')
  let response: Response
  try{
    response = await fetch(path, {
      ...init,
      headers,
      credentials:'same-origin',
      body: json=== undefined ? undefined : JSON.stringify(json)
    })
  } catch{
    throw new ApiRequestError("网络错误，请确认后端服务正在运行", 0)
  }
  if(!response.ok){
    if(version === sessionVersion && requireAuth && response.status === 401&& !expired){
      expired = true
      unauthorizedHandler?.()
    }
    const data: unknown = await response.json().catch(() => null)
    throw new ApiRequestError(detailMessage(data, fallbackMessage), response.status)
  }
  if (response.status === 204) return undefined as T
  try {
    return (await response.json()) as T
  } catch {
    throw new ApiRequestError('服务器返回的数据格式不正确，请稍后重试。', response.status)
  }
}