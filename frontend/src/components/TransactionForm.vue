<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request, errorMessage } from '../api/client'
import type { MoneyType, Account, Category, Transaction } from '../types'

const props = defineProps<{
  isRefreshing: boolean
}>()

const emit = defineEmits<{
  created: []
}>()

const moneyType = ref<MoneyType>('支出')
const amount = ref<number | null>(null)
const categoryId = ref<number | null>(null)
const accountId = ref<number | null>(null)
const description = ref('')
const transactionDate = ref('')
const accounts = ref<Account[]>([])
const categories = ref<Category[]>([])
const isOptionsLoading = ref(true)
const optionsError = ref('')
const isSubmitting = ref(false)
const submitError = ref('')
const newAccountName = ref('')
const newCategoryName = ref('')
const isCreatingAccount = ref(false)
const isCreatingCategory = ref(false)
const savedNotice = ref('')
const isBusy = computed(
  () =>
    props.isRefreshing ||
    isOptionsLoading.value ||
    isSubmitting.value ||
    isCreatingAccount.value ||
    isCreatingCategory.value,
)

const submitLabel = computed(() => {
  if (isSubmitting.value) return '保存中…'
  if (isOptionsLoading.value) return '读取中…'
  return '保存记录'
})

async function loadAccounts() {
  accounts.value = await request<Account[]>('/api/accounts')

  accountId.value = accounts.value[0]?.id ?? null
}

async function loadCategories() {
  categories.value = []
  categoryId.value = null

  const query = encodeURIComponent(moneyType.value)
  categories.value = await request<Category[]>(`/api/categories?money_type=${query}`)

  categoryId.value = categories.value[0]?.id ?? null
}

async function loadOptions() {
  isOptionsLoading.value = true
  optionsError.value = ''

  try {
    const results = await Promise.allSettled([loadAccounts(), loadCategories()])
    const failed = results.find((result) => result.status === 'rejected')
    if (failed?.status === 'rejected') throw failed.reason
  } catch (error) {
    console.error(error)
    optionsError.value = errorMessage(error, '读取账户或分类失败。')
  } finally {
    isOptionsLoading.value = false
  }
}

async function createAccount() {
  if (isBusy.value) return
  const name = newAccountName.value.trim()

  if (!name) {
    optionsError.value = '请输入账户名称。'
    return
  }

  isCreatingAccount.value = true
  optionsError.value = ''

  try {
    const account = await request<Account>('/api/accounts', {
      method: 'POST',
      json: { name_accounts: name },
      fallbackMessage: '创建账户失败。',
    })
    accounts.value.push(account)
    accountId.value = account.id
    newAccountName.value = ''
  } catch (error) {
    console.error(error)
    optionsError.value = errorMessage(error, '创建账户失败。')
  } finally {
    isCreatingAccount.value = false
  }
}

async function createCategory() {
  if (isBusy.value) return
  const name = newCategoryName.value.trim()

  if (!name) {
    optionsError.value = '请输入分类名称。'
    return
  }

  isCreatingCategory.value = true
  optionsError.value = ''

  try {
    const category = await request<Category>('/api/categories', {
      method: 'POST',
      json: { name_categories: name, money_type: moneyType.value },
      fallbackMessage: '创建分类失败。',
    })
    categories.value.push(category)
    categoryId.value = category.id
    newCategoryName.value = ''
  } catch (error) {
    console.error(error)
    optionsError.value = errorMessage(error, '创建分类失败。')
  } finally {
    isCreatingCategory.value = false
  }
}

function resetForm() {
  amount.value = null
  description.value = ''
  transactionDate.value = ''
  submitError.value = ''
}

async function selectMoneyType(value: MoneyType) {
  if (isBusy.value || moneyType.value === value) return

  moneyType.value = value
  isOptionsLoading.value = true
  optionsError.value = ''

  try {
    await loadCategories()
  } catch (error) {
    console.error(error)
    optionsError.value = errorMessage(error, '读取分类失败。')
  } finally {
    isOptionsLoading.value = false
  }
}

async function handleSubmit() {
  if (isBusy.value) return
  savedNotice.value = ''
  submitError.value = ''

  if (
    accountId.value === null ||
    categoryId.value === null ||
    typeof amount.value !== 'number' ||
    !Number.isFinite(amount.value) ||
    amount.value <= 0 ||
    !transactionDate.value
  ) {
    submitError.value = '请完整填写交易信息。'
    return
  }

  isSubmitting.value = true

  try {
    await request<Transaction>('/api/transactions', {
      method: 'POST',
      fallbackMessage: '保存记录失败。',
      json: {
        account_id: accountId.value,
        category_id: categoryId.value,
        money: amount.value,
        money_type: moneyType.value,
        description: description.value || null,
        transaction_date: transactionDate.value,
      },
    })

    resetForm()

    savedNotice.value = '保存成功。列表仍显示所选月份，其他月份的记录请切换月份查看。'
    emit('created')
  } catch (error) {
    console.error(error)
    submitError.value = errorMessage(error, '保存记录失败。')
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  loadOptions()
})
</script>

<template>
  <aside class="panel form-panel">
    <h2 class="panel-title">新增一笔记录</h2>

    <form @submit.prevent="handleSubmit">
      <fieldset class="form-grid" :disabled="isBusy">
        <div class="type-switch">
          <button
            type="button"
            :class="{ active: moneyType === '支出' }"
            @click="selectMoneyType('支出')"
          >
            支出
          </button>
          <button
            type="button"
            :class="{ active: moneyType === '收入' }"
            @click="selectMoneyType('收入')"
          >
            收入
          </button>
        </div>

        <label>
          金额
          <input
            v-model.number="amount"
            type="number"
            min="0.01"
            max="9999999.99"
            step="0.01"
            placeholder="0.00"
            required
          />
        </label>

        <label>
          分类
          <select v-model.number="categoryId" :disabled="isOptionsLoading" required>
            <option :value="null" disabled>请选择分类</option>
            <option v-for="category in categories" :key="category.id" :value="category.id">
              {{ category.name_categories }}
            </option>
          </select>
        </label>

        <div class="quick-create">
          <input
            v-model.trim="newCategoryName"
            type="text"
            maxlength="100"
            placeholder="新分类名称"
            :disabled="isCreatingCategory"
            @keydown.enter.prevent="createCategory"
          />
          <button
            type="button"
            :disabled="isCreatingCategory || isOptionsLoading"
            @click="createCategory"
          >
            {{ isCreatingCategory ? '创建中…' : '新增分类' }}
          </button>
        </div>

        <label>
          备注（可选）
          <input v-model.trim="description" maxlength="30" placeholder="例如：周末咖啡" />
        </label>

        <div class="two-col">
          <label>
            日期
            <input v-model="transactionDate" type="date" required />
          </label>
          <label>
            账户
            <select v-model.number="accountId" :disabled="isOptionsLoading" required>
              <option :value="null" disabled>请选择账户</option>
              <option v-for="account in accounts" :key="account.id" :value="account.id">
                {{ account.name_accounts }}
              </option>
            </select>
          </label>
        </div>

        <div class="quick-create">
          <input
            v-model.trim="newAccountName"
            type="text"
            maxlength="100"
            placeholder="新账户名称"
            :disabled="isCreatingAccount"
            @keydown.enter.prevent="createAccount"
          />
          <button
            type="button"
            :disabled="isCreatingAccount || isOptionsLoading"
            @click="createAccount"
          >
            {{ isCreatingAccount ? '创建中…' : '新增账户' }}
          </button>
        </div>

        <p v-if="optionsError" class="form-error">{{ optionsError }}</p>
        <button v-if="optionsError" type="button" @click="loadOptions">重新读取账户和分类</button>

        <p v-if="submitError" class="form-error">{{ submitError }}</p>

        <div class="form-actions">
          <button class="submit" type="submit" :disabled="isOptionsLoading || isSubmitting">
            {{ submitLabel }}
          </button>
        </div>
      </fieldset>
    </form>
    <p v-if="savedNotice" class="save-notice" role="status">{{ savedNotice }}</p>
  </aside>
</template>

<style scoped>
.panel {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--card);
}

.form-panel {
  position: sticky;
  top: 20px;
  padding: 25px;
}

.panel-title {
  margin: 0 0 23px;
  font-size: 17px;
  font-weight: 600;
}

.form-grid {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
  display: grid;
  gap: 17px;
}

.type-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 3px;
  border-radius: 10px;
  background: #f2f2ee;
}

.type-switch button {
  padding: 8px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
}

.type-switch button.active {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.quick-create {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.quick-create button {
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  color: var(--sage);
  font-size: 12px;
  font-weight: 600;
}

.quick-create button:hover {
  background: var(--sage-soft);
}

.quick-create button:disabled {
  cursor: wait;
  opacity: 0.6;
}

.submit {
  margin-top: 6px;
  padding: 13px;
  border: 0;
  border-radius: 10px;
  background: var(--ink);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

.submit:hover {
  background: var(--sage);
}

.submit:disabled {
  cursor: wait;
  opacity: 0.6;
}

.form-actions {
  display: grid;
  grid-template-columns: 1fr;
  align-items: end;
  gap: 10px;
}

.form-actions .submit {
  width: 100%;
}

.save-notice {
  color: var(--sage);
  font-size: 12px;
  line-height: 1.5;
}

.form-error {
  margin: 0;
  color: var(--rose);
  font-size: 12px;
}

@media (max-width: 820px) {
  .form-panel {
    position: static;
  }
}
</style>
