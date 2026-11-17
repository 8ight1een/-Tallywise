import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { readPending } from '../ai'
import { AuthContext } from '../auth'
import { queryClient } from '../query'
import type { TransactionInput } from '../types'

const payload: TransactionInput = {
  account_id: 1,
  category_id: 2,
  money: '25.00',
  money_type: '支出',
  description: '午饭',
  transaction_date: '2026-11-16',
}
const result = {
  status: 'ready',
  fields: { ...payload, single_transaction: true, question: null },
  transaction: payload,
  issues: [],
  prompt_version: 'test',
}
let posts: { key: string | null; payload: TransactionInput }[]
let failSave: boolean
let saveStatus: number
let failCatalog: boolean
let draftStatus: number

function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function openAssistant() {
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={{
        session: { status: 'user', user: { id: 1, email: 'test@example.com', nickname: '测试' } },
        login: vi.fn(), logout: vi.fn(), retry: vi.fn(), busy: false, message: '',
      }}>
        <MemoryRouter initialEntries={['/assistant']}><App /></MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
}

async function generateDraft() {
  fireEvent.change(screen.getByLabelText('描述一笔收支'), { target: { value: '今天午饭 25 元，用现金' } })
  await waitFor(() => expect((screen.getByRole('button', { name: '生成草稿' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '生成草稿' }))
  await screen.findByRole('button', { name: '确认入账' })
}

beforeEach(() => {
  posts = []
  failSave = false
  saveStatus = 201
  failCatalog = false
  draftStatus = 200
  sessionStorage.clear()
  queryClient.clear()
  vi.stubGlobal('fetch', vi.fn(async (input: string, init?: RequestInit) => {
    if (input === '/api/ai/transaction-draft') {
      return draftStatus === 200 ? response(result) : response({ detail: { message: 'AI 尚未启用，请手动记账' } }, draftStatus)
    }
    if (input === '/api/transactions' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body)) as TransactionInput
      posts.push({ key: new Headers(init.headers).get('Idempotency-Key'), payload: body })
      if (failSave) throw new TypeError('Failed to fetch')
      if (saveStatus >= 400) return response({ detail: '请求正在处理中，请稍后重试' }, saveStatus)
      return response({ ...body, id: 7, created_at: '2026-11-16T12:00:00' }, saveStatus)
    }
    if (input === '/api/accounts') {
      return failCatalog ? response({ detail: '账户读取失败' }, 403)
        : response([{ id: 1, name_accounts: '现金', created_at: '2026-11-01' }])
    }
    if (input.startsWith('/api/categories?')) {
      return response(input.includes(encodeURIComponent('支出'))
        ? [{ id: 2, name_categories: '餐饮', money_type: '支出', created_at: '2026-11-01' }]
        : [])
    }
    throw new Error('Unexpected request: ' + input)
  }))
})

afterEach(() => {
  cleanup()
  queryClient.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  sessionStorage.clear()
})

describe('AI 助手路由与入账流程', () => {
  it('导航可达，生成草稿不会入账，确认时保存用户修改后的内容', async () => {
    openAssistant()
    expect(screen.getByRole('link', { name: 'AI 助手' }).getAttribute('href')).toBe('/assistant')
    await generateDraft()
    expect(posts).toHaveLength(0)
    fireEvent.change(screen.getByLabelText('金额'), { target: { value: '30.50' } })
    fireEvent.click(screen.getByRole('button', { name: '确认入账' }))
    await screen.findByRole('heading', { name: '这一笔，记好了。' })
    expect(posts).toHaveLength(1)
    expect(posts[0].payload.money).toBe('30.50')
    expect(posts[0].key).toBeTruthy()
    expect(readPending(1)).toBeNull()
    expect(screen.getByRole('link', { name: '查看这月账单' }).getAttribute('href')).toBe('/transactions?month=2026-11')
  })

  it('断网后重新进入页面，目录读取失败仍可用同一编号和内容重试', async () => {
    failSave = true
    const view = openAssistant()
    await generateDraft()
    fireEvent.click(screen.getByRole('button', { name: '确认入账' }))
    await screen.findByText(/暂时无法确认入账结果/)
    expect(readPending(1)?.key).toBe(posts[0].key)
    view.unmount()
    queryClient.clear()
    failSave = false
    failCatalog = true
    openAssistant()
    await screen.findByText('账户读取失败')
    fireEvent.click(screen.getByRole('button', { name: '重试同一笔提交' }))
    await screen.findByRole('heading', { name: '这一笔，记好了。' })
    expect(posts).toHaveLength(2)
    expect(posts[1]).toEqual(posts[0])
    expect(readPending(1)).toBeNull()
  })

  it('持续冲突时只有用户核对并明确确认才结束追踪，不会再次入账', async () => {
    saveStatus = 409
    openAssistant()
    await generateDraft()
    fireEvent.click(screen.getByRole('button', { name: '确认入账' }))
    await screen.findByText(/暂时无法确认入账结果/)
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    fireEvent.click(screen.getByRole('button', { name: '已核对账本，结束本次提交' }))
    expect(readPending(1)).not.toBeNull()
    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', { name: '已核对账本，结束本次提交' }))
    await screen.findByText('已结束本次提交，账本中的记录未作更改。')
    expect(readPending(1)).toBeNull()
    expect(posts).toHaveLength(1)
    expect((screen.getByLabelText('描述一笔收支') as HTMLTextAreaElement).disabled).toBe(false)
  })

  it('清除本地追踪失败时保持锁定，避免丢失重试编号', async () => {
    failSave = true
    openAssistant()
    await generateDraft()
    fireEvent.click(screen.getByRole('button', { name: '确认入账' }))
    await screen.findByText(/暂时无法确认入账结果/)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('Storage blocked') })
    fireEvent.click(screen.getByRole('button', { name: '已核对账本，结束本次提交' }))
    await screen.findByText('浏览器无法清除待确认记录，请恢复会话存储后再试。')
    expect(readPending(1)?.key).toBe(posts[0].key)
    expect((screen.getByLabelText('描述一笔收支') as HTMLTextAreaElement).disabled).toBe(true)
  })

  it('会话存储不可写时不发送入账请求', async () => {
    openAssistant()
    await generateDraft()
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage blocked') })
    fireEvent.click(screen.getByRole('button', { name: '确认入账' }))
    await screen.findByText(/尚未发送入账请求/)
    expect(posts).toHaveLength(0)
  })

  it('成功入账后目录刷新失败会告知用户，保留成功结果', async () => {
    openAssistant()
    await generateDraft()
    failCatalog = true
    fireEvent.click(screen.getByRole('button', { name: '确认入账' }))
    await screen.findByRole('heading', { name: '这一笔，记好了。' })
    await screen.findByText('已入账，数据刷新失败，请在账本页点击“刷新数据”。')
    expect(posts).toHaveLength(1)
    expect(readPending(1)).toBeNull()
  })

  it('AI 接口报错时显示后端说明并允许手动记账', async () => {
    draftStatus = 503
    openAssistant()
    fireEvent.change(screen.getByLabelText('描述一笔收支'), { target: { value: '午饭 25 元' } })
    await waitFor(() => expect((screen.getByRole('button', { name: '生成草稿' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: '生成草稿' }))
    await screen.findByText('AI 尚未启用，请手动记账')
    expect((screen.getByRole('button', { name: '手动记账' }) as HTMLButtonElement).disabled).toBe(false)
    expect(posts).toHaveLength(0)
  })
})
