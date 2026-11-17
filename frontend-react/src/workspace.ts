export type Page = 'overview' | 'transactions' | 'accounts' | 'categories' | 'assistant'
export const labels = {
  overview: '账本概览',
  transactions: '收支明细',
  accounts: '我的账户',
  categories: '收支分类',
  assistant: 'AI 助手',
}
export const navIcons: Record<Page, string> = {
  overview: 'grid',
  transactions: 'list',
  accounts: 'wallet',
  categories: 'tag',
  assistant: 'leaf',
}
