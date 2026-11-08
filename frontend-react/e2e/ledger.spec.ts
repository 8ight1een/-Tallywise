import { expect, test } from '@playwright/test'

const email = `e2e-${Date.now()}@example.com`
const password = 'e2e-password'

test('注册登录后可以新增、编辑、删除流水', async ({ page }) => {
  await page.goto('/register')
  await page.getByLabel('昵称').fill('E2E')
  await page.getByLabel('邮箱地址').fill(email)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '创建账户' }).click()
  await expect(page).toHaveURL(/\/login$/)

  await page.getByLabel('邮箱地址').fill(email)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: /登\s*录/ }).click()
  await expect(page).toHaveURL(/\/overview$/)

  const account = await page.request.post('/api/accounts', {
    data: { name_accounts: '现金' },
  })
  expect(account.status()).toBe(200)

  const category = await page.request.post('/api/categories', {
    data: { name_categories: '餐饮', money_type: '支出' },
  })
  expect(category.status()).toBe(200)

  await page.getByRole('button', { name: '刷新数据' }).click()
  await page.getByRole('button', { name: '记一笔' }).click()

  await page.getByLabel('金额').fill('12.34')
  await page.getByLabel('分类').selectOption({ label: '餐饮' })
  await page.getByLabel('账户').selectOption({ label: '现金' })
  await page.getByLabel(/备注/).fill('午餐')
  await page.getByRole('button', { name: '保存记录' }).click()

  await expect(page.getByText('午餐')).toBeVisible()
  await expect(page.getByText(/共\s*1\s*笔记录/)).toBeVisible()

  await page.getByRole('button', { name: '编辑午餐' }).click()
  await page.getByLabel('金额').fill('20')
  await page.getByRole('button', { name: '保存记录' }).click()
  await expect(page.getByRole('row', { name: /午餐/ })).toContainText('20.00')

  await page.getByRole('button', { name: '编辑午餐' }).click()
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: '删除记录' }).click()
  await expect(page.getByText('午餐')).toBeHidden()
  await expect(page.getByText(/共\s*0\s*笔记录/)).toBeVisible()
})
