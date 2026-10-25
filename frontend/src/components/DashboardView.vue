<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request, errorMessage, isUnauthorized } from '../api/client'
import SummaryCards from './SummaryCards.vue'
import TransactionList from './TransactionList.vue'
import TransactionForm from './TransactionForm.vue'
import type { User, Summary, Transaction, Category, MonthSelection } from '../types'

defineProps<{
  user: User
  isLoggingOut: boolean
}>()

const emit = defineEmits<{
  logout: []
}>()

const summary = ref<Summary | null>(null)
const isSummaryLoading = ref(true)
const summaryError = ref('')
const selectedPeriod = ref<MonthSelection>('current')
const periodLabel = computed(() =>
  selectedPeriod.value === 'current' ? '本月' : `${selectedPeriod.value}月`,
)
const transactions = ref<Transaction[]>([])
const categories = ref<Category[]>([])
const isTransactionsLoading = ref(true)
const transactionsError = ref('')
const editingTransaction = ref<Transaction | null>(null)
const deletingTransactionId = ref<number | null>(null)
const isFormBusy = ref(true)
const actionError = ref('')
const actionNotice = ref('')
const isActionBusy = computed(
  () =>
    isSummaryLoading.value ||
    isTransactionsLoading.value ||
    isFormBusy.value ||
    deletingTransactionId.value !== null,
)
let summaryRequestVersion = 0
let transactionsRequestVersion = 0

function getQueryPeriod() {
  const now = new Date()
  return {
    year: now.getFullYear(),
    month: selectedPeriod.value === 'current' ? now.getMonth() + 1 : selectedPeriod.value,
  }
}

async function loadSummary(year: number, month: number) {
  const version = ++summaryRequestVersion
  isSummaryLoading.value = true
  summaryError.value = ''

  try {
    const result = await request<Summary>(`/api/summary?year=${year}&month=${month}`)
    if (version === summaryRequestVersion) summary.value = result
  } catch (error) {
    console.error(error)
    if (version === summaryRequestVersion)
      summaryError.value = errorMessage(error, '读取月度汇总失败。')
  } finally {
    if (version === summaryRequestVersion) isSummaryLoading.value = false
  }
}

async function loadTransactions(year: number, month: number) {
  const version = ++transactionsRequestVersion
  isTransactionsLoading.value = true
  transactionsError.value = ''

  try {
    const [records, incomeCategories, expenseCategories] = await Promise.all([
      request<Transaction[]>(`/api/transactions/${year}/${month}`),
      request<Category[]>(`/api/categories?money_type=${encodeURIComponent('收入')}`),
      request<Category[]>(`/api/categories?money_type=${encodeURIComponent('支出')}`),
    ])
    if (version === transactionsRequestVersion) {
      transactions.value = records
      categories.value = [...incomeCategories, ...expenseCategories]
    }
  } catch (error) {
    console.error(error)
    if (version === transactionsRequestVersion)
      transactionsError.value = errorMessage(error, '读取交易记录失败。')
  } finally {
    if (version === transactionsRequestVersion) isTransactionsLoading.value = false
  }
}

async function refreshFinancialData() {
  const { year, month } = getQueryPeriod()
  await Promise.all([loadSummary(year, month), loadTransactions(year, month)])
}

async function changePeriod(value: MonthSelection) {
  if (isActionBusy.value || editingTransaction.value !== null) return
  if (value === selectedPeriod.value) return
  selectedPeriod.value = value
  await refreshFinancialData()
}

function startEditing(transaction: Transaction) {
  if (isActionBusy.value || editingTransaction.value !== null) return
  if (!window.confirm('进入编辑将清空当前新增表单的内容，是否继续？')) return
  actionError.value = ''
  actionNotice.value = ''
  editingTransaction.value = { ...transaction }
}

function cancelEditing() {
  if (isActionBusy.value) return
  editingTransaction.value = null
}

async function handleTransactionSaved() {
  const wasEditing = editingTransaction.value !== null
  editingTransaction.value = null
  actionError.value = ''
  actionNotice.value = wasEditing ? '记录已更新。若更改了日期，请在对应月份查看。' : '记录已保存。'
  await refreshFinancialData()
}

async function deleteTransaction(transaction: Transaction) {
  if (isActionBusy.value || editingTransaction.value !== null) return
  if (!window.confirm(`确定删除“${transaction.description || '这笔记录'}”吗？此操作无法撤销。`))
    return
  deletingTransactionId.value = transaction.id
  actionError.value = ''
  actionNotice.value = ''
  try {
    await request(`/api/transactions/${transaction.id}`, {
      method: 'DELETE',
      fallbackMessage: '删除记录失败。',
    })
    actionNotice.value = '记录已删除。'
    await refreshFinancialData()
  } catch (error) {
    if (!isUnauthorized(error)) actionError.value = errorMessage(error, '删除记录失败。')
  } finally {
    deletingTransactionId.value = null
  }
}

onMounted(refreshFinancialData)
</script>

<template>
  <main class="app">
    <header>
      <div class="brand">
        <span class="brand-mark"></span>
        Tallywise
      </div>

      <div class="header-right">
        <div class="user-info">
          <span class="user-nickname">
            {{ user.nickname }}
          </span>

          <span class="user-email">
            {{ user.email }}
          </span>
        </div>

        <button
          class="logout-button"
          type="button"
          :disabled="isLoggingOut"
          @click="emit('logout')"
        >
          {{ isLoggingOut ? '退出中…' : '退出登录' }}
        </button>
      </div>
    </header>

    <section class="greeting">
      <h1>你的财务，一目了然。</h1>
      <p>记录每一笔微小的流动，让生活保持从容。</p>
    </section>

    <SummaryCards
      :summary="summary"
      :is-loading="isSummaryLoading"
      :error-message="summaryError"
      :period-label="periodLabel"
    />

    <p v-if="actionError" class="auth-error" role="alert">{{ actionError }}</p>
    <p v-if="actionNotice" role="status">{{ actionNotice }}</p>
    <section class="content">
      <TransactionForm
        :key="editingTransaction?.id ?? 'new'"
        :editing-transaction="editingTransaction"
        :is-refreshing="isSummaryLoading || isTransactionsLoading || deletingTransactionId !== null"
        @busy-change="isFormBusy = $event"
        @created="handleTransactionSaved"
        @updated="handleTransactionSaved"
        @cancel-edit="cancelEditing"
      />
      <TransactionList
        :transactions="transactions"
        :categories="categories"
        :is-loading="isTransactionsLoading"
        :error-message="transactionsError"
        :selected-period="selectedPeriod"
        :is-period-loading="isActionBusy || editingTransaction !== null"
        :is-action-disabled="isActionBusy || editingTransaction !== null"
        :deleting-transaction-id="deletingTransactionId"
        @month-change="changePeriod"
        @edit-request="startEditing"
        @delete-request="deleteTransaction"
      />
    </section>
  </main>
</template>

<style scoped>
.content {
  display: grid;
  grid-template-columns: 350px minmax(0, 1fr);
  align-items: start;
  gap: 28px;
}

@media (max-width: 820px) {
  .content {
    grid-template-columns: 1fr;
  }
}
</style>
